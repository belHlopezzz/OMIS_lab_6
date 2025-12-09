// components/Layout/Layout.js
import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import './Layout.css';

const Layout = ({ children, onLogout }) => {
  const navigate = useNavigate();
  const location = useLocation();
  const { user } = useAuth();

  const menuItems = [
    { path: '/', icon: '⊞', label: 'Дашборд' },
    { path: '/devices', icon: '⚙', label: 'Устройства' },
    { path: '/events', icon: '🔔', label: 'События' },
    { path: '/reports', icon: '📊', label: 'Отчёты' }
  ];

  const getRoleLabel = (userType) => {
    const labels = {
      operator: 'Оператор',
      administrator: 'Администратор',
      manager: 'Менеджер'
    };
    return labels[userType] || userType;
  };

  return (
    <div className="layout">
      <header className="header">
        <div className="header-left">
          <div className="logo">
            <div className="logo-icon">⊟</div>
            <span className="logo-text">IoT Monitor</span>
          </div>
        </div>
        <div className="header-right">
          {user && (
            <div className="user-info">
              <span className="user-name">{user.username}</span>
              <span className="user-role">{getRoleLabel(user.user_type)}</span>
            </div>
          )}
          <button className="user-button" onClick={onLogout} title="Выйти">
            <span className="user-icon">👤</span>
          </button>
        </div>
      </header>

      <div className="main-container">
        <aside className="sidebar">
          <nav className="sidebar-nav">
            {menuItems.map((item) => (
              <button
                key={item.path}
                className={`nav-item ${location.pathname === item.path ? 'active' : ''}`}
                onClick={() => navigate(item.path)}
              >
                <span className="nav-icon">{item.icon}</span>
                <span className="nav-label">{item.label}</span>
              </button>
            ))}
          </nav>
        </aside>

        <main className="content">
          {children}
        </main>
      </div>
    </div>
  );
};

export default Layout;
