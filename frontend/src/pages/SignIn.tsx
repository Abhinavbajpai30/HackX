import { Particles } from "@/components/ui/particles";
import { ParticleButton } from "@/components/ui/particle-button";
import { useCallback } from "react";
import { useAuthValidation } from "@/hooks/use-auth-validation";

const BACKEND_URL = (import.meta as any).env?.VITE_BACKEND_URL || "http://localhost:8000";

const SignIn = () => {
  useAuthValidation();
  const startGoogleLogin = useCallback(async () => {
    try {
      const res = await fetch(`${BACKEND_URL}/auth/login`, {
        headers: {
          "ngrok-skip-browser-warning": "true"
        }
      });
      if (!res.ok) throw new Error("Failed to start login");
      const data: { authorization_url: string; state: string } = await res.json();
      window.location.href = data.authorization_url;
    } catch (e) {
      console.error(e);
      alert("Could not start Google sign-in. Please try again.");
    }
  }, []);

  return (
    <div className="relative min-h-screen bg-background flex items-center justify-center overflow-hidden">
      <Particles className="absolute inset-0 z-0" quantity={120} staticity={50} size={1} color="#6F00FF" />
      <div className="relative z-10 w-full max-w-lg px-6 text-center">
         <div className="rounded-xl border bg-card px-16 py-12">
        <h1 className="font-serif text-4xl md:text-5xl font-bold text-foreground mb-3 leading-tight">
          Welcome back!
        </h1>
        <p className="text-sm text-muted-foreground mb-6">Sign in to continue with Google</p>
       
          <ParticleButton onClick={startGoogleLogin} className="w-full h-11 rounded-full">
            Continue with Google
          </ParticleButton>
        </div>
      </div>
    </div>
  );
};

export default SignIn;
