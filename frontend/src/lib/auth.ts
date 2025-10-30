// Authentication utilities for frontend
import { useState, useEffect } from 'react';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export interface UserInfo {
  authenticated: boolean;
  email: string;
  user_info: {
    email: string;
    name?: string;
    picture?: string;
    given_name?: string;
    family_name?: string;
  };
  last_login: string | null;
  watch_active: boolean;
  watch_expires: string | null;
  last_sync: string | null;
  email_count: number;
}

export class AuthService {
  private static TOKEN_KEY = 'auth_token';

  /**
   * Store authentication token in localStorage
   */
  static setToken(token: string): void {
    localStorage.setItem(this.TOKEN_KEY, token);
  }

  /**
   * Get authentication token from localStorage
   */
  static getToken(): string | null {
    return localStorage.getItem(this.TOKEN_KEY);
  }

  /**
   * Remove authentication token from localStorage
   */
  static clearToken(): void {
    localStorage.removeItem(this.TOKEN_KEY);
  }

  /**
   * Check if user is authenticated (has valid token)
   */
  static isAuthenticated(): boolean {
    return !!this.getToken();
  }

  /**
   * Get current user information from backend
   */
  static async getCurrentUser(): Promise<UserInfo | null> {
    const token = this.getToken();
    if (!token) {
      return null;
    }

    try {
      const response = await fetch(`${API_BASE_URL}/auth/me`, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        if (response.status === 401) {
          // Token expired or invalid
          this.clearToken();
          return null;
        }
        throw new Error(`Failed to get user info: ${response.statusText}`);
      }

      const data = await response.json();
      return data;
    } catch (error) {
      console.error('Error fetching current user:', error);
      return null;
    }
  }

  /**
   * Initiate Google OAuth login
   */
  static async initiateLogin(): Promise<void> {
    try {
      const response = await fetch(`${API_BASE_URL}/auth/login`, {
        method: 'GET',
      });

      if (!response.ok) {
        throw new Error('Failed to initiate login');
      }

      const data = await response.json();
      // Redirect to Google OAuth
      window.location.href = data.authorization_url;
    } catch (error) {
      console.error('Error initiating login:', error);
      throw error;
    }
  }

  /**
   * Handle OAuth callback and extract token from URL
   */
  static handleCallback(): string | null {
    const urlParams = new URLSearchParams(window.location.search);
    const token = urlParams.get('token');
    
    if (token) {
      this.setToken(token);
      // Clean up URL
      window.history.replaceState({}, document.title, window.location.pathname);
      return token;
    }
    
    return null;
  }

  /**
   * Logout current user
   */
  static async logout(): Promise<void> {
    const token = this.getToken();
    if (!token) {
      return;
    }

    try {
      const response = await fetch(`${API_BASE_URL}/auth/logout`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        console.error('Logout request failed:', response.statusText);
      }
    } catch (error) {
      console.error('Error during logout:', error);
    } finally {
      // Always clear token locally
      this.clearToken();
    }
  }

  /**
   * Make authenticated API request
   */
  static async authenticatedFetch(endpoint: string, options: RequestInit = {}): Promise<Response> {
    const token = this.getToken();
    if (!token) {
      throw new Error('No authentication token available');
    }

    const headers = {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
      ...options.headers,
    };

    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      ...options,
      headers,
    });

    if (response.status === 401) {
      // Token expired, clear it
      this.clearToken();
      throw new Error('Authentication expired');
    }

    return response;
  }
}

// React Hook for authentication
export function useAuth() {
  const [user, setUser] = useState<UserInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadUser() {
      try {
        setLoading(true);
        const userData = await AuthService.getCurrentUser();
        setUser(userData);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load user');
      } finally {
        setLoading(false);
      }
    }

    loadUser();
  }, []);

  const login = async () => {
    await AuthService.initiateLogin();
  };

  const logout = async () => {
    await AuthService.logout();
    setUser(null);
  };

  return {
    user,
    loading,
    error,
    isAuthenticated: !!user,
    login,
    logout,
  };
}
