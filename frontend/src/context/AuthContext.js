/**
 * Контекст аутентификации.
 * Управляет состоянием авторизации и данными пользователя.
 */
import React, { createContext, useContext, useState, useEffect } from 'react';
import { authAPI } from '../api';

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(localStorage.getItem('token'));
  const [loading, setLoading] = useState(true);

  // Проверяем токен при загрузке
  useEffect(() => {
    const initAuth = async () => {
      if (token) {
        try {
          const userData = await authAPI.getCurrentUser();
          setUser(userData);
        } catch (error) {
          // Токен невалидный
          localStorage.removeItem('token');
          localStorage.removeItem('user');
          setToken(null);
          setUser(null);
        }
      }
      setLoading(false);
    };

    initAuth();
  }, [token]);

  const login = async (email, password) => {
    const response = await authAPI.login(email, password);
    
    localStorage.setItem('token', response.access_token);
    localStorage.setItem('user', JSON.stringify(response.user));
    
    setToken(response.access_token);
    setUser(response.user);
    
    return response.user;
  };

  const logout = async () => {
    try {
      await authAPI.logout();
    } catch (error) {
      // Игнорируем ошибки при выходе
    }
    
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    
    setToken(null);
    setUser(null);
  };

  const isAuthenticated = !!token && !!user;

  // Проверка ролей
  const hasRole = (roles) => {
    if (!user) return false;
    if (typeof roles === 'string') {
      return user.user_type === roles;
    }
    return roles.includes(user.user_type);
  };

  const isOperator = () => hasRole(['operator', 'administrator', 'manager']);
  const isAdmin = () => hasRole(['administrator', 'manager']);
  const isManager = () => hasRole('manager');

  const value = {
    user,
    token,
    loading,
    isAuthenticated,
    login,
    logout,
    hasRole,
    isOperator,
    isAdmin,
    isManager,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth должен использоваться внутри AuthProvider');
  }
  return context;
};

export default AuthContext;

