/** Inline script to apply theme before paint — prevents flash. */
export function ThemeScript() {
  const script = `
    (function() {
      try {
        var t = localStorage.getItem('securisphere-theme');
        var theme = t === 'light' ? 'light' : 'dark';
        document.documentElement.setAttribute('data-theme', theme);
        document.documentElement.classList.add(theme);
      } catch(e) {}
    })();
  `;
  return <script dangerouslySetInnerHTML={{ __html: script }} />;
}
