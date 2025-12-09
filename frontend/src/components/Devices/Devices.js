// components/Devices/Devices.js
import React, { useState, useEffect, useCallback } from 'react';
import { equipmentAPI, sensorsAPI, predictionsAPI, authAPI } from '../../api';
import { useAuth } from '../../context/AuthContext';
import './Devices.css';

const Devices = () => {
  const [devices, setDevices] = useState([]);
  const [selectedDevice, setSelectedDevice] = useState(null);
  const [deviceHistory, setDeviceHistory] = useState([]);
  const [sensorData, setSensorData] = useState({});
  const [prediction, setPrediction] = useState(null);
  const [filterStatus, setFilterStatus] = useState('all');
  const [loading, setLoading] = useState(true);
  const [modalLoading, setModalLoading] = useState(false);
  const [showAddModal, setShowAddModal] = useState(false);
  const [showMaintenanceModal, setShowMaintenanceModal] = useState(false);
  const [operators, setOperators] = useState([]);
  const [error, setError] = useState(null);
  
  const { isAdmin } = useAuth();

  // Форма нового оборудования
  const [newEquipment, setNewEquipment] = useState({
    name: '',
    type: '',
    location: '',
    description: ''
  });

  // Форма обслуживания
  const [maintenanceForm, setMaintenanceForm] = useState({
    description: '',
    technician: '',
    technicianId: ''
  });
  
  // Статус оборудования для изменения
  const [statusUpdate, setStatusUpdate] = useState('');

  const fetchDevices = useCallback(async () => {
    try {
      setLoading(true);
      const data = await equipmentAPI.getAll(filterStatus);
      
      const formattedDevices = data.map(eq => ({
        id: eq.id,
        equipment_id: eq.equipment_id,
        name: eq.name,
        type: eq.type,
        status: eq.status,
        location: eq.location,
        sensors: eq.sensors || [],
        current_metrics: eq.current_metrics || {},
        lastUpdate: eq.last_update 
          ? new Date(eq.last_update).toLocaleString('ru-RU')
          : 'Нет данных'
      }));
      
      setDevices(formattedDevices);
      setError(null);
    } catch (err) {
      console.error('Ошибка загрузки устройств:', err);
      setError('Не удалось загрузить список устройств');
    } finally {
      setLoading(false);
    }
  }, [filterStatus]);

  useEffect(() => {
    fetchDevices();
    const interval = setInterval(fetchDevices, 60000);
    return () => clearInterval(interval);
  }, [fetchDevices]);

  const openDeviceDetail = async (device) => {
    setSelectedDevice(device);
    setModalLoading(true);
    setPrediction(null);
    setStatusUpdate(device.status);
    
    try {
      // Загружаем историю обслуживания
      const history = await equipmentAPI.getHistory(device.id);
      setDeviceHistory(history);
      
      // Загружаем данные датчиков за последние 24 часа
      const sensors = await sensorsAPI.getData(device.id, null, 24);
      setSensorData(sensors);

      // Получаем список операторов (техников)
      const ops = await authAPI.getOperators();
      setOperators(ops);
    } catch (err) {
      console.error('Ошибка загрузки деталей:', err);
    } finally {
      setModalLoading(false);
    }
  };

  const runPrediction = async () => {
    if (!selectedDevice) return;
    
    setModalLoading(true);
    try {
      const result = await predictionsAPI.predict(selectedDevice.id);
      setPrediction(result);
    } catch (err) {
      console.error('Ошибка прогнозирования:', err);
      alert('Не удалось выполнить прогнозирование');
    } finally {
      setModalLoading(false);
    }
  };

  const handleAddEquipment = async (e) => {
    e.preventDefault();
    try {
      await equipmentAPI.create(newEquipment);
      setShowAddModal(false);
      setNewEquipment({ name: '', type: '', location: '', description: '' });
      fetchDevices();
    } catch (err) {
      console.error('Ошибка создания оборудования:', err);
      alert('Не удалось создать оборудование');
    }
  };

  const handleAddMaintenance = async (e) => {
    e.preventDefault();
    if (!selectedDevice) return;
    
    try {
      const response = await fetch(`http://localhost:8000/api/equipment/${selectedDevice.id}/maintenance`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify({
          equipment_id: selectedDevice.id,
          date: new Date().toISOString().split('T')[0],
          ...maintenanceForm,
          technician: maintenanceForm.technician || maintenanceForm.technicianId || ''
        })
      });
      
      if (response.ok) {
        setShowMaintenanceModal(false);
        setMaintenanceForm({ description: '', technician: '' });
        // Обновляем историю
        const history = await equipmentAPI.getHistory(selectedDevice.id);
        setDeviceHistory(history);
      }
    } catch (err) {
      console.error('Ошибка добавления записи:', err);
    }
  };

  const handleStatusUpdate = async () => {
    if (!selectedDevice) return;
    try {
      await equipmentAPI.updateStatus(selectedDevice.id, statusUpdate);
      // Обновляем список и выбранное устройство
      await fetchDevices();
      setSelectedDevice(prev => prev ? { ...prev, status: statusUpdate } : prev);
    } catch (err) {
      console.error('Ошибка обновления статуса:', err);
      alert('Не удалось обновить статус');
    }
  };

  const getStatusLabel = (status) => {
    const labels = {
      error: 'Авария',
      offline: 'Оффлайн',
      online: 'Онлайн',
      maintenance: 'Обслуживание'
    };
    return labels[status] || status;
  };

  const getRiskLevelClass = (level) => {
    const classes = {
      critical: 'risk-critical',
      high: 'risk-high',
      medium: 'risk-medium',
      low: 'risk-low'
    };
    return classes[level] || '';
  };

  const getRiskLevelLabel = (level) => {
    const labels = {
      critical: 'Критический',
      high: 'Высокий',
      medium: 'Средний',
      low: 'Низкий'
    };
    return labels[level] || level;
  };

  return (
    <div className="devices">
      <div className="devices-header">
        <h1 className="page-title">Устройства</h1>
        <div className="header-actions">
          {isAdmin() && (
            <button className="add-btn" onClick={() => setShowAddModal(true)}>
              + Добавить оборудование
            </button>
          )}
          <div className="filter-dropdown">
            <button className="filter-button">
              <span className="filter-icon">⚡</span>
              <span>{filterStatus === 'all' ? 'Все статусы' : getStatusLabel(filterStatus)}</span>
              <span className="dropdown-icon">▼</span>
            </button>
            <div className="filter-menu">
              <button onClick={() => setFilterStatus('all')}>Все статусы</button>
              <button onClick={() => setFilterStatus('online')}>Онлайн</button>
              <button onClick={() => setFilterStatus('offline')}>Оффлайн</button>
              <button onClick={() => setFilterStatus('error')}>Авария</button>
              <button onClick={() => setFilterStatus('maintenance')}>Обслуживание</button>
            </div>
          </div>
        </div>
      </div>

      {error && <div className="error-banner">{error}</div>}

      {loading && devices.length === 0 ? (
        <div className="loading-placeholder">Загрузка устройств...</div>
      ) : (
        <div className="devices-table-container">
          <table className="devices-table">
            <thead>
              <tr>
                <th>Название</th>
                <th>Тип</th>
                <th>Статус</th>
                <th>Последнее обновление</th>
                <th>Действия</th>
              </tr>
            </thead>
            <tbody>
              {devices.length === 0 ? (
                <tr>
                  <td colSpan="5" className="no-data">Устройства не найдены</td>
                </tr>
              ) : (
                devices.map(device => (
                  <tr key={device.id}>
                    <td className="device-name">{device.name}</td>
                    <td className="device-type">{device.type}</td>
                    <td>
                      <span className={`status-badge status-${device.status}`}>
                        {getStatusLabel(device.status)}
                      </span>
                    </td>
                    <td className="device-update">{device.lastUpdate}</td>
                    <td>
                      <button 
                        className="detail-btn"
                        onClick={() => openDeviceDetail(device)}
                      >
                        Подробнее
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* Модальное окно деталей устройства */}
      {selectedDevice && (
        <div className="modal-overlay" onClick={() => setSelectedDevice(null)}>
          <div className="modal-content device-modal" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h2>{selectedDevice.name}</h2>
              <button className="close-btn" onClick={() => setSelectedDevice(null)}>×</button>
            </div>
            
            <div className="modal-body">
              <div className="device-info">
                <div className="info-row">
                  <span className="info-label">ID:</span>
                  <span>{selectedDevice.equipment_id}</span>
                </div>
                <div className="info-row">
                  <span className="info-label">Тип:</span>
                  <span>{selectedDevice.type}</span>
                </div>
                <div className="info-row">
                  <span className="info-label">Статус:</span>
                  <span className={`status-badge status-${selectedDevice.status}`}>
                    {getStatusLabel(selectedDevice.status)}
                  </span>
                </div>
                <div className="info-row">
                  <span className="info-label">Расположение:</span>
                  <span>{selectedDevice.location || 'Не указано'}</span>
                </div>
              </div>

              {/* Текущие показатели датчиков */}
              <div className="section">
                <h3>Текущие показатели</h3>
                {modalLoading ? (
                  <p>Загрузка...</p>
                ) : (
                  <div className="metrics-grid">
                    {Object.entries(selectedDevice.current_metrics || {}).map(([type, data]) => (
                      <div key={type} className="metric-card">
                        <div className="metric-type">{type}</div>
                        <div className="metric-value">{data.value} {data.unit}</div>
                      </div>
                    ))}
                    {Object.keys(selectedDevice.current_metrics || {}).length === 0 && (
                      <p className="no-data-text">Нет данных с датчиков</p>
                    )}
                  </div>
                )}
              </div>

              {/* Прогнозирование */}
              <div className="section">
                <div className="section-header">
                  <h3>Прогнозирование отказа</h3>
                  {isAdmin() && (
                    <button className="action-btn" onClick={runPrediction} disabled={modalLoading}>
                      Запустить анализ
                    </button>
                  )}
                </div>
                
                {prediction && (
                  <div className="prediction-result">
                    <div className={`risk-badge ${getRiskLevelClass(prediction.failure_prediction.risk_level)}`}>
                      Риск: {getRiskLevelLabel(prediction.failure_prediction.risk_level)}
                    </div>
                    <div className="prediction-details">
                      <p>Вероятность отказа: <strong>{Math.round(prediction.failure_prediction.probability * 100)}%</strong></p>
                      <p>Горизонт прогноза: {prediction.failure_prediction.time_window_hours} часов</p>
                    </div>
                    {prediction.failure_prediction.factors.length > 0 && (
                      <div className="factors">
                        <h4>Факторы риска:</h4>
                        <ul>
                          {prediction.failure_prediction.factors.map((f, i) => (
                            <li key={i}>{f}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                    {prediction.recommendations.length > 0 && (
                      <div className="recommendations">
                        <h4>Рекомендации:</h4>
                        <ul>
                          {prediction.recommendations.map((r, i) => (
                            <li key={i}>{r}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                )}
              </div>

              {/* История обслуживания */}
              <div className="section">
                <div className="section-header">
                  <h3>История обслуживания</h3>
                  <button className="action-btn" onClick={() => setShowMaintenanceModal(true)}>
                    + Добавить запись
                  </button>
                </div>
                
                {deviceHistory.length > 0 ? (
                  <div className="history-list">
                    {deviceHistory.slice(0, 5).map(record => (
                      <div key={record.id} className="history-item">
                        <div className="history-date">{record.date}</div>
                        <div className="history-desc">{record.description}</div>
                        <div className="history-tech">Техник: {record.technician}</div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="no-data-text">Нет записей об обслуживании</p>
                )}
              </div>

              {/* Обновление статуса оборудования */} 
              <div className="section">
                <div className="section-header">
                  <h3>Статус оборудования</h3>
                  <button className="action-btn" onClick={handleStatusUpdate} disabled={modalLoading}>
                    Сохранить статус
                  </button>
                </div>
                <div className="form-group">
                  <label>Статус</label>
                  <select
                    value={statusUpdate}
                    onChange={e => setStatusUpdate(e.target.value)}
                  >
                    <option value="online">Онлайн</option>
                    <option value="maintenance">Обслуживание</option>
                    <option value="offline">Оффлайн</option>
                    <option value="error">Авария</option>
                  </select>
                  <p className="hint-text">Операторы могут отмечать ремонт и возвращать прибор в онлайн.</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Модальное окно добавления оборудования */}
      {showAddModal && (
        <div className="modal-overlay" onClick={() => setShowAddModal(false)}>
          <div className="modal-content form-modal" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h2>Новое оборудование</h2>
              <button className="close-btn" onClick={() => setShowAddModal(false)}>×</button>
            </div>
            <form onSubmit={handleAddEquipment}>
              <div className="form-group">
                <label>Название *</label>
                <input
                  type="text"
                  value={newEquipment.name}
                  onChange={e => setNewEquipment({...newEquipment, name: e.target.value})}
                  required
                />
              </div>
              <div className="form-group">
                <label>Тип *</label>
                <select
                  value={newEquipment.type}
                  onChange={e => setNewEquipment({...newEquipment, type: e.target.value})}
                  required
                >
                  <option value="">Выберите тип</option>
                  <option value="Турбина">Турбина</option>
                  <option value="Компрессор">Компрессор</option>
                  <option value="Насос">Насос</option>
                  <option value="Электродвигатель">Электродвигатель</option>
                  <option value="Конвейер">Конвейер</option>
                </select>
              </div>
              <div className="form-group">
                <label>Расположение</label>
                <input
                  type="text"
                  value={newEquipment.location}
                  onChange={e => setNewEquipment({...newEquipment, location: e.target.value})}
                />
              </div>
              <div className="form-group">
                <label>Описание</label>
                <textarea
                  value={newEquipment.description}
                  onChange={e => setNewEquipment({...newEquipment, description: e.target.value})}
                />
              </div>
              <div className="form-actions">
                <button type="button" className="cancel-btn" onClick={() => setShowAddModal(false)}>
                  Отмена
                </button>
                <button type="submit" className="submit-btn">Создать</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Модальное окно добавления обслуживания */}
      {showMaintenanceModal && (
        <div className="modal-overlay" onClick={() => setShowMaintenanceModal(false)}>
          <div className="modal-content form-modal" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h2>Добавить запись об обслуживании</h2>
              <button className="close-btn" onClick={() => setShowMaintenanceModal(false)}>×</button>
            </div>
            <form onSubmit={handleAddMaintenance}>
              <div className="form-group">
                <label>Описание работ *</label>
                <textarea
                  value={maintenanceForm.description}
                  onChange={e => setMaintenanceForm({...maintenanceForm, description: e.target.value})}
                  required
                />
              </div>
              <div className="form-group">
                <label>Оператор (техник) *</label>
                <select
                  value={maintenanceForm.technicianId}
                  onChange={e => {
                    const techId = e.target.value;
                    const tech = operators.find(o => String(o.id) === techId);
                    setMaintenanceForm({
                      ...maintenanceForm,
                      technicianId: techId,
                      technician: tech ? tech.username : ''
                    });
                  }}
                  required
                >
                  <option value="">Выберите оператора</option>
                  {operators.map(op => (
                    <option key={op.id} value={op.id}>
                      {op.username} ({op.email})
                    </option>
                  ))}
                </select>
              </div>
              <div className="form-actions">
                <button type="button" className="cancel-btn" onClick={() => setShowMaintenanceModal(false)}>
                  Отмена
                </button>
                <button type="submit" className="submit-btn">Добавить</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default Devices;
