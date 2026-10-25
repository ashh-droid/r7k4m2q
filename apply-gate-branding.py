"""Apply a modest Gate wordmark/icon enlargement without changing other page styles.

Run from the project root: python apply-gate-branding.py
"""
from pathlib import Path
import shutil

css_file = Path('frontend/src/styles/app.css')
if not css_file.is_file():
    raise SystemExit('Could not find frontend/src/styles/app.css. Run this from the Gate project folder.')

patch_marker = '/* Gate identity: a restrained increase in scale and a sharper, heavier gate mark. */'
css = css_file.read_text(encoding='utf-8')
if patch_marker in css:
    print('Branding update is already present. No changes made.')
else:
    snippet = '''/* Gate identity: a restrained increase in scale and a sharper, heavier gate mark. */
.wordmark {
  gap: 12px;
  font-size: clamp(1.38rem, 1.12rem + 0.82vw, 1.8rem);
  font-weight: 650;
  line-height: 1;
  letter-spacing: -0.015em;
  white-space: nowrap;
}

.wordmark svg {
  width: 32px;
  height: 32px;
  flex: 0 0 auto;
}

.wordmark svg path {
  stroke-width: 2.45px;
  stroke-linecap: round;
  stroke-linejoin: round;
}

@media (max-width: 720px) {
  .wordmark {
    gap: 10px;
    font-size: 1.35rem;
  }

  .wordmark svg {
    width: 28px;
    height: 28px;
  }
}
'''
    backup = css_file.with_suffix('.css.before-branding.bak')
    shutil.copy2(css_file, backup)
    css_file.write_text(css.rstrip() + '\n\n' + snippet, encoding='utf-8')
    print('Updated:', css_file)
    print('Backup:', backup)
    print('Run: docker compose up --build')
