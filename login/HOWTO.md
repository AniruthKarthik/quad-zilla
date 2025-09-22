# Frontend-Backend Integration Guide

## API Endpoints

| Method | Endpoint | Auth Required | Request Body | Response |
|--------|----------|---------------|--------------|----------|
| **POST** | `/auth/register` | ❌ | `{username, email, password}` | `{message, user_id}` |
| **POST** | `/auth/login` | ❌ | `{username, password}` | `{access_token, token_type, user}` |
| **GET** | `/auth/me` | ✅ | None | `{id, username, email, is_active, created_at}` |
| **POST** | `/auth/change-password` | ✅ | `{current_password, new_password}` | `{message}` |
| **POST** | `/auth/forgot-password` | ❌ | `{email}` | `{message}` |
| **POST** | `/auth/reset-password/{token}` | ❌ | `{new_password}` | `{message}` |
| **POST** | `/auth/logout` | ✅ | None | `{message}` |
| **DELETE** | `/auth/deactivate` | ✅ | None | `{message}` |
| **GET** | `/auth/validate-token` | ✅ | None | `{valid, user_id}` |
| **GET** | `/health` | ❌ | None | `{status}` |

**Auth Header Format**: `Authorization: Bearer {token}`

## Frontend Integration

### JavaScript/Fetch
```javascript
const API_URL = 'YOUR_API_URL'; // Replace with your backend URL

class AuthService {
  constructor() {
    this.token = localStorage.getItem('access_token');
  }

  async request(endpoint, options = {}) {
    const headers = { 'Content-Type': 'application/json', ...options.headers };
    if (this.token) headers.Authorization = `Bearer ${this.token}`;

    const response = await fetch(`${API_URL}${endpoint}`, { ...options, headers });
    if (!response.ok) throw new Error((await response.json()).detail);
    return response.json();
  }

  async register(username, email, password) {
    return this.request('/auth/register', {
      method: 'POST',
      body: JSON.stringify({ username, email, password })
    });
  }

  async login(username, password) {
    const data = await this.request('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, password })
    });
    this.token = data.access_token;
    localStorage.setItem('access_token', this.token);
    return data;
  }

  async getCurrentUser() {
    return this.request('/auth/me');
  }

  async changePassword(currentPassword, newPassword) {
    return this.request('/auth/change-password', {
      method: 'POST',
      body: JSON.stringify({ current_password: currentPassword, new_password: newPassword })
    });
  }

  logout() {
    this.token = null;
    localStorage.removeItem('access_token');
  }
}

const auth = new AuthService();
```

### React
```jsx
import { createContext, useContext, useState } from 'react';

const AuthContext = createContext();
const API_URL = 'YOUR_API_URL'; // Replace with your backend URL

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(localStorage.getItem('access_token'));

  const request = async (endpoint, options = {}) => {
    const headers = { 'Content-Type': 'application/json', ...options.headers };
    if (token) headers.Authorization = `Bearer ${token}`;

    const response = await fetch(`${API_URL}${endpoint}`, { ...options, headers });
    if (!response.ok) throw new Error((await response.json()).detail);
    return response.json();
  };

  const login = async (username, password) => {
    const data = await request('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, password })
    });
    setToken(data.access_token);
    setUser(data.user);
    localStorage.setItem('access_token', data.access_token);
    return data;
  };

  const logout = () => {
    setToken(null);
    setUser(null);
    localStorage.removeItem('access_token');
  };

  return (
    <AuthContext.Provider value={{ user, login, logout, request }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
```

### Axios
```javascript
import axios from 'axios';

const api = axios.create({
  baseURL: 'YOUR_API_URL', // Replace with your backend URL
});

// Add token to requests
api.interceptors.request.use(config => {
  const token = localStorage.getItem('access_token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// Handle token expiration
api.interceptors.response.use(
  response => response,
  error => {
    if (error.response?.status === 401) {
      localStorage.removeItem('access_token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export default api;
```

## Usage Examples

### Login
```javascript
// JavaScript
const result = await auth.login('username', 'password');

// React
const { login } = useAuth();
await login('username', 'password');

// Axios
const response = await api.post('/auth/login', { username, password });
localStorage.setItem('access_token', response.data.access_token);
```

### Protected Request
```javascript
// JavaScript
const user = await auth.getCurrentUser();

// React
const { request } = useAuth();
const user = await request('/auth/me');

// Axios
const user = await api.get('/auth/me');
```

**Replace `YOUR_API_URL` with your actual backend URL** (e.g., `https://your-api.herokuapp.com`, `http://localhost:8000`, etc.)
