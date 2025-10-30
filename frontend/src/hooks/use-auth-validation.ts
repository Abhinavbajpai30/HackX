import { useEffect, useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { AuthService, UserInfo } from '@/lib/auth';

export function useAuthValidation() {
  const [user, setUser] = useState<UserInfo | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    const validateAuth = async () => {
      try {
        // Handle OAuth callback - extract token from URL and save to localStorage
        const token = AuthService.handleCallback();
        if (token) {
          console.log('✅ JWT token found in URL and saved to localStorage');
        }

        // Verify token is valid by fetching current user
        const currentUser = await AuthService.getCurrentUser();

        if (currentUser) {
          console.log('✅ JWT token is valid. User data:', currentUser);
          setUser(currentUser);

          // Redirect authenticated users away from auth pages
          if (location.pathname === '/signin' || location.pathname === '/signup') {
            console.log('ℹ️ User already authenticated. Redirecting to dashboard.');
            navigate('/dashboard', { replace: true });
          }
        } else {
          console.warn('⚠️ JWT token is invalid or expired. Clearing localStorage.');
          AuthService.clearToken();
          setUser(null);
        }
      } catch (error) {
        console.error('❌ Auth validation failed:', error);
        AuthService.clearToken();
        setUser(null);
      } finally {
        setIsLoading(false);
      }
    };

    validateAuth();
  }, [navigate, location.pathname]);

  return { user, isLoading };
}
