/** Inline script to apply theme before paint — prevents flash. */
export function ThemeScript() {
  const script = `
    (function() {
      try {
        var t = localStorage.getItem('securisphere-theme');
        var theme = t === 'light' ? 'light' : 'dark';
        document.documentElement.setAttribute('data-theme', theme);
        document.documentElement.classList.add(theme);
        var m = localStorage.getItem('securisphere-reduced-motion');
        var reduced = m === 'true' ? true : m === 'false' ? false : window.matchMedia('(prefers-reduced-motion: reduce)').matches;
        document.documentElement.setAttribute('data-reduced-motion', reduced ? 'true' : 'false');
      } catch(e) {}
    })();
  `;
  return <script dangerouslySetInnerHTML={{ __html: script }} />;
}
