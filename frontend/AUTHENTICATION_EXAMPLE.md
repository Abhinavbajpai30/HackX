# Authentication Implementation Guide

This guide shows how to use the authentication system in your React frontend.

## Overview

The backend now uses JWT tokens for session management. After OAuth login, users receive a token that's valid for 7 days.

## Backend Endpoints

### New Endpoints

1. **GET `/auth/me`** - Get current user info (requires authentication)
   - Headers: `Authorization: Bearer <token>`
   - Returns: User info including email, profile, stats

2. **POST `/auth/logout`** - Logout current user (requires authentication)
   - Headers: `Authorization: Bearer <token>`
   - Returns: Success message

3. **GET `/auth/login`** - Initiate OAuth flow
   - Returns: Authorization URL to redirect to

4. **GET `/auth/callback`** - OAuth callback handler
   - Redirects to frontend with token: `/dashboard?token=<jwt_token>`

## Frontend Setup

### 1. Install Dependencies

The authentication utilities are already created in `frontend/src/lib/auth.ts`.

### 2. Environment Variables

Create `frontend/.env` with:

```bash
VITE_API_URL=http://localhost:8000
```

### 3. Usage in React Components

#### Basic Usage with Hook

```typescript
import { useAuth } from '@/lib/auth';

function MyComponent() {
  const { user, loading, isAuthenticated, login, logout } = useAuth();

  if (loading) {
    return <div>Loading...</div>;
  }

  if (!isAuthenticated) {
    return (
      <div>
        <button onClick={login}>Login with Google</button>
      </div>
    );
  }

  return (
    <div>
      <h1>Welcome, {user.user_info.name || user.email}!</h1>
      <p>Email: {user.email}</p>
      <p>Total Emails: {user.email_count}</p>
      <button onClick={logout}>Logout</button>
    </div>
  );
}
```

#### Handle OAuth Callback in Dashboard

```typescript
import { useEffect } from 'react';
import { AuthService } from '@/lib/auth';
import { useNavigate } from 'react-router-dom';

function Dashboard() {
  const navigate = useNavigate();

  useEffect(() => {
    // Check for token in URL (OAuth callback)
    const token = AuthService.handleCallback();
    if (token) {
      console.log('User logged in successfully');
      // Token is now stored, reload to fetch user info
      window.location.reload();
    }
  }, []);

  const { user, loading, isAuthenticated } = useAuth();

  if (loading) {
    return <div>Loading...</div>;
  }

  if (!isAuthenticated) {
    navigate('/signin');
    return null;
  }

  return (
    <div>
      <h1>Dashboard</h1>
      <p>Welcome, {user.user_info.name}!</p>
    </div>
  );
}
```

#### Protected Route Component

```typescript
import { Navigate } from 'react-router-dom';
import { AuthService } from '@/lib/auth';

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  if (!AuthService.isAuthenticated()) {
    return <Navigate to="/signin" />;
  }

  return <>{children}</>;
}

// Usage in App.tsx
<Route 
  path="/dashboard" 
  element={
    <ProtectedRoute>
      <Dashboard />
    </ProtectedRoute>
  } 
/>
```

#### Making Authenticated API Calls

```typescript
import { AuthService } from '@/lib/auth';

async function fetchUserEmails() {
  try {
    const response = await AuthService.authenticatedFetch('/user/emails');
    
    if (!response.ok) {
      throw new Error('Failed to fetch emails');
    }
    
    const data = await response.json();
    return data.emails;
  } catch (error) {
    if (error.message === 'Authentication expired') {
      // Redirect to login
      window.location.href = '/signin';
    }
    throw error;
  }
}
```

#### Sign In Page Example

```typescript
import { AuthService } from '@/lib/auth';
import { Button } from '@/components/ui/button';

function SignIn() {
  const handleGoogleLogin = () => {
    AuthService.initiateLogin();
  };

  return (
    <div className="flex items-center justify-center min-h-screen">
      <div className="text-center">
        <h1 className="text-3xl font-bold mb-6">Welcome to HackX</h1>
        <Button onClick={handleGoogleLogin} size="lg">
          Sign in with Google
        </Button>
      </div>
    </div>
  );
}
```

## Token Management

### Token Storage

Tokens are stored in `localStorage` under the key `auth_token`.

### Token Expiration

- Tokens expire after 7 days
- When a token expires, API calls return 401 and the frontend automatically clears the token
- Users need to log in again

### Logout

When users log out:
1. Backend marks the logout timestamp
2. Token is removed from localStorage
3. User is redirected to sign-in page

## User Info Structure

```typescript
interface UserInfo {
  authenticated: boolean;
  email: string;
  user_info: {
    email: string;
    name?: string;
    picture?: string;           // Profile picture URL
    given_name?: string;        // First name
    family_name?: string;       // Last name
  };
  last_login: string | null;
  watch_active: boolean;
  watch_expires: string | null;
  last_sync: string | null;
  email_count: number;
}
```

## Testing

### 1. Start Backend
```bash
cd backend
python main.py
```

### 2. Start Frontend
```bash
cd frontend
npm run dev
```

### 3. Test Flow

1. Navigate to sign-in page
2. Click "Sign in with Google"
3. Complete Google OAuth
4. Get redirected to dashboard with token
5. Token is stored automatically
6. Make authenticated requests
7. Test logout

## Security Notes

1. **JWT Secret**: Set `JWT_SECRET_KEY` in backend `.env` for production
2. **HTTPS**: Use HTTPS in production to protect tokens
3. **Token Storage**: Consider using `httpOnly` cookies for production (more secure than localStorage)
4. **CORS**: Lock down CORS origins in production
5. **Token Refresh**: Consider implementing refresh tokens for better UX

## Troubleshooting

### Token not being set after OAuth

Check browser console for the token parameter in URL after redirect from Google.

### 401 errors on authenticated endpoints

- Check if token is in localStorage: `localStorage.getItem('auth_token')`
- Verify Authorization header is being sent: Check Network tab in DevTools
- Ensure backend JWT_SECRET_KEY hasn't changed

### User logged out unexpectedly

- Token may have expired (7 days)
- User may have logged out from another tab
- Check `logged_out_at` timestamp in database
