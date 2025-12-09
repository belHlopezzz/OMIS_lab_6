// components/Events/Events.js
import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { eventsAPI } from '../../api';
import './Events.css';

const Events = () => {
  const [events, setEvents] = useState([]);
  const [stats, setStats] = useState(null);
  const [filterLevel, setFilterLevel] = useState('all');
  const [refreshSeconds, setRefreshSeconds] = useState(10);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const navigate = useNavigate();

  const fetchEvents = useCallback(async () => {
    try {
      setLoading(true);
      const [eventsData, statsData] = await Promise.all([
        eventsAPI.getAll(filterLevel),
        eventsAPI.getStats()
      ]);
      setEvents(eventsData);
      setStats(statsData);
      setError(null);
    } catch (err) {
      console.error('Ошибка загрузки событий:', err);
      setError('Не удалось загрузить события');
    } finally {
      setLoading(false);
    }
  }, [filterLevel]);

  useEffect(() => {
    fetchEvents();
    
    // Обновляем каждые 30 секунд
    const interval = setInterval(fetchEvents, refreshSeconds * 1000);
    return () => clearInterval(interval);
  }, [fetchEvents, refreshSeconds]);

  const handleFilterChange = (newLevel) => {
    setFilterLevel(newLevel);
  };

  const handleMarkRead = async (eventId) => {
    try {
      await eventsAPI.markRead(eventId);
      fetchEvents(); // Обновляем список
    } catch (err) {
      console.error('Ошибка отметки события:', err);
    }
  };

  const handleMarkAllRead = async () => {
    try {
      await eventsAPI.markAllRead();
      fetchEvents();
    } catch (err) {
      console.error('Ошибка отметки всех событий:', err);
    }
  };

  const handleGoToDevice = (deviceName) => {
    // Переходим на страницу устройств
    navigate('/devices');
    // Можно было бы передать ID устройства, но для простоты просто переходим
  };

  const getFilterLabel = () => {
    const labels = {
      all: 'Все уровни',
      critical: 'Критично',
      warning: 'Предупреждение'
    };
    return labels[filterLevel] || 'Все уровни';
  };

  return (
    <div className="events">
      <div className="events-header">
        <div>
          <h1 className="page-title">События и оповещения</h1>
          <p className="page-subtitle">
            Автоматические уведомления о превышении пороговых значений датчиков, 
            аномалиях и критических состояниях оборудования
          </p>
        </div>
        <div className="header-actions">
          <div className="refresh-control">
            <label>Обновлять каждые:</label>
            <select value={refreshSeconds} onChange={e => setRefreshSeconds(Number(e.target.value))}>
              <option value={5}>5 сек</option>
              <option value={10}>10 сек</option>
              <option value={20}>20 сек</option>
              <option value={30}>30 сек</option>
            </select>
          </div>
          {stats && stats.unread_count > 0 && (
            <button className="mark-all-btn" onClick={handleMarkAllRead}>
              Отметить все прочитанными ({stats.unread_count})
            </button>
          )}
          <div className="filter-dropdown">
            <button className="filter-button">
              {getFilterLabel()}
              <span className="dropdown-icon">▼</span>
            </button>
            <div className="filter-menu">
              <button onClick={() => handleFilterChange('all')}>Все уровни</button>
              <button onClick={() => handleFilterChange('critical')}>Критично</button>
              <button onClick={() => handleFilterChange('warning')}>Предупреждение</button>
            </div>
          </div>
        </div>
      </div>

      {/* Статистика */}
      {stats && (
        <div className="events-stats">
          <div className="stat-card">
            <div className="stat-value">{stats.unread_count}</div>
            <div className="stat-label">Непрочитанных</div>
          </div>
          <div className="stat-card">
            <div className="stat-value critical">{stats.critical_unread}</div>
            <div className="stat-label">Критических</div>
          </div>
          <div className="stat-card">
            <div className="stat-value">{stats.today_count}</div>
            <div className="stat-label">Сегодня</div>
          </div>
          <div className="stat-card">
            <div className="stat-value">{stats.week_count}</div>
            <div className="stat-label">За неделю</div>
          </div>
        </div>
      )}

      {error && <div className="error-banner">{error}</div>}

      {/* Информационный блок если нет событий */}
      {!loading && events.length === 0 && (
        <div className="info-box">
          <div className="info-icon">ℹ️</div>
          <div className="info-content">
            <h3>Нет событий</h3>
            <p>
              События создаются автоматически когда:
            </p>
            <ul>
              <li>Датчики превышают пороговые значения (температура, вибрация, давление, ток)</li>
              <li>Обнаруживаются аномалии в данных</li>
              <li>Оборудование переходит в критическое состояние</li>
            </ul>
            <p className="info-note">
              Система проверяет показания каждые 30 секунд. 
              Если все оборудование работает нормально, событий не будет.
            </p>
          </div>
        </div>
      )}

      {loading && events.length === 0 ? (
        <div className="loading-placeholder">Загрузка событий...</div>
      ) : events.length > 0 ? (
        <>
          <div className="events-list-title">
            Лента событий ({events.length})
          </div>
          <div className="events-list">
            {events.map(event => (
              <div key={event.id} className={`event-card event-${event.type}`}>
                <div className="event-icon">
                  {event.type === 'critical' ? '⊗' : '⚠'}
                </div>
                <div className="event-content">
                  <div className="event-header-row">
                    <span className="event-badge">
                      {event.type === 'critical' ? 'Критично' : 'Предупреждение'}
                    </span>
                    <span className="event-timestamp">{event.timestamp}</span>
                  </div>
                  <div className="event-device">
                    <button 
                      className="device-link"
                      onClick={() => handleGoToDevice(event.device)}
                      title="Перейти к оборудованию"
                    >
                      {event.device} →
                    </button>
                  </div>
                  <div className="event-message">{event.message}</div>
                  <div className="event-actions">
                    <button 
                      className="action-link"
                      onClick={() => handleMarkRead(event.id)}
                    >
                      Отметить прочитанным
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </>
      ) : null}
    </div>
  );
};

export default Events;
