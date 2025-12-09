// components/Dashboard/Dashboard.js
import React, { useState, useEffect, useCallback } from 'react';
import { dashboardAPI } from '../../api';
import './Dashboard.css';

const Dashboard = () => {
  const [stats, setStats] = useState({
    total_devices: 0,
    online_devices: 0,
    error_devices: 0
  });

  const [temperatureData, setTemperatureData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchDashboardData = useCallback(async () => {
    try {
      setLoading(true);
      
      // Загружаем статистику и данные графика параллельно
      const [statsData, chartData] = await Promise.all([
        dashboardAPI.getStats(),
        dashboardAPI.getTemperatureChart()
      ]);

      setStats({
        total_devices: statsData.total_devices,
        online_devices: statsData.online_devices,
        error_devices: statsData.error_devices
      });

      // Преобразуем данные для графика
      if (chartData.data && chartData.data.length > 0) {
        setTemperatureData(chartData.data.map(point => ({
          time: point.time,
          temp: point.value
        })));
      } else {
        // Если данных нет, показываем заглушку
        setTemperatureData([
    { time: '00:00', temp: 22 },
    { time: '04:00', temp: 22 },
    { time: '08:00', temp: 23.5 },
    { time: '12:00', temp: 25.2 },
    { time: '16:00', temp: 24.5 },
    { time: '20:00', temp: 23 },
    { time: '24:00', temp: 22.5 }
  ]);
      }

      setError(null);
    } catch (err) {
      console.error('Ошибка загрузки данных дашборда:', err);
      setError('Не удалось загрузить данные');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchDashboardData();
    
    // Обновляем данные каждые 30 секунд
    const interval = setInterval(fetchDashboardData, 30000);
    return () => clearInterval(interval);
  }, [fetchDashboardData]);

  const maxTemp = temperatureData.length > 0 
    ? Math.max(...temperatureData.map(d => d.temp)) 
    : 30;
  const minTemp = temperatureData.length > 0 
    ? Math.min(...temperatureData.map(d => d.temp)) 
    : 20;

  if (loading && stats.total_devices === 0) {
    return (
      <div className="dashboard">
        <h1 className="page-title">Обзор системы</h1>
        <div className="loading-placeholder">Загрузка данных...</div>
      </div>
    );
  }

  return (
    <div className="dashboard">
      <h1 className="page-title">Обзор системы</h1>

      {error && <div className="error-banner">{error}</div>}

      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-icon gray">⚙</div>
          <div className="stat-content">
            <div className="stat-value">{stats.total_devices}</div>
            <div className="stat-label">Всего устройств</div>
            <div className="stat-sublabel">В системе мониторинга</div>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon green">✓</div>
          <div className="stat-content">
            <div className="stat-value">{stats.online_devices}</div>
            <div className="stat-label">Онлайн</div>
            <div className="stat-sublabel">Активных подключений</div>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon red">⚠</div>
          <div className="stat-content">
            <div className="stat-value">{stats.error_devices}</div>
            <div className="stat-label">С ошибками</div>
            <div className="stat-sublabel">Требуют внимания</div>
          </div>
        </div>
      </div>

      <div className="chart-card">
        <div className="chart-header">
          <span className="chart-icon">📈</span>
          <h2 className="chart-title">Средняя температура системы</h2>
        </div>
        <div className="chart-container">
          <svg className="chart" viewBox="0 0 800 200">
            {/* Grid lines */}
            {[0, 1, 2, 3, 4].map(i => (
              <line
                key={i}
                x1="0"
                y1={i * 50}
                x2="800"
                y2={i * 50}
                stroke="#e5e7eb"
                strokeWidth="1"
              />
            ))}

            {/* Temperature line */}
            {temperatureData.length > 1 && (
            <polyline
              points={temperatureData.map((d, i) => {
                const x = (i / (temperatureData.length - 1)) * 800;
                  const range = maxTemp - minTemp || 1;
                  const y = 200 - ((d.temp - minTemp) / range) * 150 - 25;
                return `${x},${y}`;
              }).join(' ')}
              fill="none"
              stroke="#3b82f6"
              strokeWidth="2"
            />
            )}

            {/* Data points */}
            {temperatureData.map((d, i) => {
              const x = temperatureData.length > 1 
                ? (i / (temperatureData.length - 1)) * 800 
                : 400;
              const range = maxTemp - minTemp || 1;
              const y = 200 - ((d.temp - minTemp) / range) * 150 - 25;
              return (
                <circle
                  key={i}
                  cx={x}
                  cy={y}
                  r="4"
                  fill="#3b82f6"
                />
              );
            })}
          </svg>
          <div className="chart-labels">
            {temperatureData.map((d, i) => (
              <span key={i} className="chart-label">{d.time}</span>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
