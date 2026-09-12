from datetime import UTC, datetime, time, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqlalchemy import select

from frotad.models import Branch, Company, Driver, Vehicle
from frotad.models.forms import Form, FormField
from frotad.models.runner import FormAnswer, FormSubmission, PeriodValue
from frotad.schemas.dashboard import DailyMetrics, DashboardConfig, DashboardRead, LiveOperation
from frotad.services.runner import now, scope, utc


def read(db, context, day=None):
    # Reuse the runner's tenant, branch and assigned-driver authorization.
    visible = scope(context).with_only_columns(FormSubmission.id)
    company = db.get(Company, context.company_id)
    branch = db.get(Branch, context.branch_id) if context.branch_id else None
    timezone = (branch.timezone if branch else None) or company.timezone
    zone = ZoneInfo(timezone)
    clock = now()
    day = day or clock.astimezone(zone).date()
    config = DashboardConfig.model_validate((company.settings or {}).get("dashboard", {}))
    days = {day - timedelta(days=i): DailyMetrics(day=day - timedelta(days=i)) for i in range(7)}
    start = datetime.combine(day - timedelta(days=6), time.min, zone).astimezone(UTC)
    end = datetime.combine(day + timedelta(days=1), time.min, zone).astimezone(UTC)
    records = db.execute(
        select(FormSubmission, Form.code)
        .join(Form, Form.id == FormSubmission.form_id)
        .where(
            FormSubmission.id.in_(visible),
            FormSubmission.status == "SUBMITTED",
            FormSubmission.submitted_at >= start,
            FormSubmission.submitted_at < end,
            Form.code.in_([config.cycle_form, config.fuel_form]),
        )
    ).all()
    record_ids = [record.id for record, _ in records]
    numeric = {
        (answer.submission_id, key): answer.value_decimal
        if answer.value_decimal is not None
        else Decimal(answer.value_integer)
        for answer, key in db.execute(
            select(FormAnswer, FormField.key)
            .join(FormField, FormField.id == FormAnswer.field_id)
            .where(
                FormAnswer.company_id == context.company_id,
                FormAnswer.submission_id.in_(record_ids),
                (FormAnswer.value_decimal.is_not(None) | FormAnswer.value_integer.is_not(None)),
            )
        )
    }
    for record, code in records:
        bucket = days[utc(record.submitted_at).astimezone(zone).date()]
        if code == config.cycle_form:
            bucket.trips += 1
            if (record.id, config.volume_field) not in numeric:
                bucket.missing_measurements += 1
            bucket.volume_m3 += numeric.get((record.id, config.volume_field), Decimal(0))
        if code == config.fuel_form:
            if (record.id, config.fuel_field) not in numeric:
                bucket.missing_measurements += 1
            bucket.diesel_liters += numeric.get((record.id, config.fuel_field), Decimal(0))
    for bucket in days.values():
        if bucket.volume_m3 > 0 and not bucket.missing_measurements:
            bucket.liters_per_m3 = (bucket.diesel_liters / bucket.volume_m3).quantize(
                Decimal("0.0001")
            )
    active = []
    vehicle_ids = set()
    cycle_ids = set()
    rows = db.execute(
        select(PeriodValue, FormSubmission, FormField, Vehicle.fleet_number, Driver.name, Form.code)
        .join(FormSubmission, FormSubmission.id == PeriodValue.submission_id)
        .join(FormAnswer, FormAnswer.id == PeriodValue.answer_id)
        .join(FormField, FormField.id == FormAnswer.field_id)
        .join(Form, Form.id == FormSubmission.form_id)
        .outerjoin(Vehicle, Vehicle.id == FormSubmission.vehicle_id)
        .outerjoin(Driver, Driver.id == FormSubmission.driver_id)
        .where(
            FormSubmission.id.in_(visible),
            PeriodValue.company_id == context.company_id,
            PeriodValue.end_at.is_(None),
        )
        .order_by(PeriodValue.start_at, PeriodValue.id)
    )
    for period, record, field, vehicle, driver, code in rows:
        if record.vehicle_id:
            vehicle_ids.add(record.vehicle_id)
        if code == config.cycle_form:
            cycle_ids.add(record.id)
        active.append(
            LiveOperation(
                period_id=period.id,
                submission_id=record.id,
                vehicle=vehicle or "Sem veículo",
                driver=driver or "Sem motorista",
                status_key=period.status_key,
                status_label=field.config.get("status_label", field.label),
                started_at=utc(period.start_at),
                elapsed_seconds=max(0, int((clock - utc(period.start_at)).total_seconds())),
            )
        )
    return DashboardRead(
        company=company.name,
        timezone=timezone,
        server_time=clock,
        metrics=days[day],
        trend=[days[d] for d in sorted(days)],
        active=active,
        active_vehicles=len(vehicle_ids),
        active_cycles=len(cycle_ids),
        waiting=sum(p.status_key == config.waiting_status for p in active),
        waiting_status=config.waiting_status,
        target_liters_per_m3=config.target_liters_per_m3,
    )
