/**
 * API клиент для взаимодействия с бэкендом.
 * Централизованная конфигурация axios с interceptors для JWT.
 */
import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api';

// Создаём экземпляр axios с базовой конфигурацией
const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Interceptor для добавления токена к запросам
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Interceptor для обработки ошибок ответа
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Токен истёк или невалидный - выходим
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      window.location.href = '/';
    }
    return Promise.reject(error);
  }
);

// === Аутентификация ===

export const authAPI = {
  login: async (email, password) => {
    const response = await api.post('/auth/login', { email, password });
    return response.data;
  },
  
  logout: async () => {
    const response = await api.post('/auth/logout');
    return response.data;
  },
  
  getCurrentUser: async () => {
    const response = await api.get('/auth/me');
    return response.data;
  },
  
  getUsers: async () => {
    const response = await api.get('/auth/users');
    return response.data;
  },
  
  getOperators: async () => {
    const response = await api.get('/auth/operators');
    return response.data;
  },
};

// === Дашборд ===

export const dashboardAPI = {
  getStats: async () => {
    const response = await api.get('/dashboard/stats');
    return response.data;
  },
  
  getTemperatureChart: async () => {
    const response = await api.get('/dashboard/temperature-chart');
    return response.data;
  },
  
  getSensorStats: async () => {
    const response = await api.get('/dashboard/sensor-stats');
    return response.data;
  },
};

// === Оборудование ===

export const equipmentAPI = {
  getAll: async (statusFilter = null) => {
    const params = statusFilter && statusFilter !== 'all' 
      ? { status_filter: statusFilter } 
      : {};
    const response = await api.get('/equipment', { params });
    return response.data;
  },
  
  getById: async (id) => {
    const response = await api.get(`/equipment/${id}`);
    return response.data;
  },
  
  create: async (data) => {
    const response = await api.post('/equipment', data);
    return response.data;
  },
  
  updateStatus: async (id, status) => {
    const response = await api.put(`/equipment/${id}/status`, null, {
      params: { new_status: status }
    });
    return response.data;
  },
  
  getHistory: async (id) => {
    const response = await api.get(`/equipment/${id}/history`);
    return response.data;
  },
};

// === Датчики ===

export const sensorsAPI = {
  getData: async (equipmentId, sensorType = null, hours = 24) => {
    const params = { hours };
    if (sensorType) params.sensor_type = sensorType;
    const response = await api.get(`/sensors/${equipmentId}/data`, { params });
    return response.data;
  },
  
  addData: async (equipmentId, sensorType, value) => {
    const response = await api.post(`/sensors/${equipmentId}/data`, null, {
      params: { sensor_type: sensorType, value }
    });
    return response.data;
  },
  
  getLatest: async (equipmentId) => {
    const response = await api.get(`/sensors/${equipmentId}/latest`);
    return response.data;
  },
};

// === События ===

export const eventsAPI = {
  getAll: async (level = null, hours = 72) => {
    const params = { hours };
    if (level && level !== 'all') params.level = level;
    const response = await api.get('/events', { params });
    return response.data;
  },
  
  getAlerts: async (unreadOnly = false) => {
    const response = await api.get('/events/alerts', {
      params: { unread_only: unreadOnly }
    });
    return response.data;
  },
  
  markRead: async (alertId) => {
    const response = await api.put(`/events/${alertId}/read`);
    return response.data;
  },
  
  markAllRead: async () => {
    const response = await api.put('/events/read-all');
    return response.data;
  },
  
  getStats: async () => {
    const response = await api.get('/events/stats');
    return response.data;
  },
};

// === Отчёты ===

export const reportsAPI = {
  downloadPDF: async (periodDays = 7) => {
    const response = await api.get('/reports/pdf', {
      params: { period_days: periodDays },
      responseType: 'blob',
    });
    return response.data;
  },
  
  downloadCSV: async (dataType = 'equipment', periodDays = 7) => {
    const response = await api.get('/reports/csv', {
      params: { data_type: dataType, period_days: periodDays },
      responseType: 'blob',
    });
    return response.data;
  },
  
  getSummary: async (periodDays = 7) => {
    const response = await api.get('/reports/summary', {
      params: { period_days: periodDays }
    });
    return response.data;
  },
};

// === Прогнозирование ===

export const predictionsAPI = {
  predict: async (equipmentId, horizonHours = 48) => {
    const response = await api.post(`/predictions/${equipmentId}`, {
      equipment_id: equipmentId,
      horizon_hours: horizonHours,
    });
    return response.data;
  },
  
  detectAnomalies: async (equipmentId) => {
    const response = await api.get(`/predictions/${equipmentId}/anomalies`);
    return response.data;
  },
  
  predictAll: async () => {
    const response = await api.get('/predictions/batch');
    return response.data;
  },
};

export default api;

