import React, { useState, useEffect } from 'react';
import { Sun, Moon } from 'lucide-react';

const ThemeToggle = () => {
  const [theme, setTheme] = useState(localStorage.getItem('theme') || 'light');

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('theme', theme);
  }, [theme]);

  const toggleTheme = () => {
    setTheme(prevTheme => (prevTheme === 'light' ? 'dark' : 'light'));
  };

  return (
    <div className="theme-toggle" onClick={toggleTheme}>
      <span className="theme-toggle-label">{theme === 'light' ? 'Dark' : 'Light'} Mode</span>
      <div className="theme-toggle-icon">
        {theme === 'light' ? <Moon size={18} /> : <Sun size={18} />}
      </div>
    </div>
  );
};

export default ThemeToggle;
