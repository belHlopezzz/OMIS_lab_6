// components/Login/Login.js
import React, { useState } from 'react';
import { useAuth } from '../../context/AuthContext';
import './Login.css';

const Login = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  
  const { login } = useAuth();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    if (!email || !password) {
      setError('Пожалуйста, заполните все поля');
      return;
    }

    setLoading(true);

    try {
      await login(email, password);
    } catch (err) {
      const errorMessage = err.response?.data?.detail || 'Ошибка входа. Проверьте данные.';
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-container">
      <div className="login-card">
        <div className="login-logo">
          <div className="login-logo-icon">⊟</div>
        </div>
        <h1 className="login-title">IoT Monitor</h1>
        <p className="login-subtitle">
          Интеллектуальная система прогнозирования<br />
          поломок оборудования
        </p>
        <div className="login-description">
          Система мониторит состояние IoT-устройств в<br />
          реальном времени и автоматически отправляет<br />
          уведомления о проблемах и аномалиях.
        </div>

        <form onSubmit={handleSubmit} className="login-form">
          <div className="form-group">
            <label className="form-label">Email</label>
            <input
              type="email"
              className="form-input"
              placeholder="your@email.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              disabled={loading}
            />
          </div>

          <div className="form-group">
            <label className="form-label">Пароль</label>
            <input
              type="password"
              className="form-input"
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              disabled={loading}
            />
          </div>

          {error && <div className="error-message">{error}</div>}

          <button type="submit" className="login-button" disabled={loading}>
            {loading ? 'Вход...' : 'Войти'}
          </button>
        </form>

        <div className="demo-credentials">
          <p>Тестовые учётные записи:</p>
          <ul>
            <li>operator@test.com / operator123</li>
            <li>admin@test.com / admin123</li>
            <li>manager@test.com / manager123</li>
          </ul>
        </div>
      </div>
    </div>
  );
};

export default Login;
