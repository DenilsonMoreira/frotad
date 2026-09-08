# Design System

## Direção visual inicial

A identidade inicial utiliza azul e azul-acinzentado para transmitir confiança, controle, estabilidade e profissionalismo industrial. O tema não deve depender de uma marca de cliente específico.

A customização futura deve ser baseada em tokens.

## Tokens sugeridos

```css
:root {
  --color-brand-950: #10263f;
  --color-brand-900: #173552;
  --color-brand-700: #315c82;
  --color-brand-500: #5f86a8;
  --color-brand-100: #e8f0f6;
  --color-surface: #ffffff;
  --color-surface-muted: #f4f7f9;
  --color-text: #15263a;
  --color-text-muted: #657487;
  --color-border: #dbe3ea;
}
```

Status semantic colors may use restrained green/amber/red only when they communicate state. The application must also use labels/icons; never color alone.

## Theme model

Later:

- company logo;
- primary color;
- navigation color;
- accent color;
- light/dark preference;
- optional white-label.

Keep layout/component structure stable across themes.

## Driver UX

- large controls;
- minimum typing;
- obvious Start/Finish period buttons;
- persistent current status;
- prevent accidental double starts;
- show elapsed time;
- work at small widths;
- clear sync state once offline support exists.
