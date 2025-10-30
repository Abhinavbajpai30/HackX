import { Link } from "react-router-dom";
import { Bell } from "lucide-react";
import { Button } from "@/components/ui/button";

export default function NavBar() {
  const isSignedIn = typeof window !== "undefined" && localStorage.getItem("signedIn") === "true";

  return (
    <nav className="fixed top-0 inset-x-0 z-30 bg-white/80 backdrop-blur supports-[backdrop-filter]:bg-white/70 border-b">
      <div className="mx-auto max-w-6xl px-6 h-14 flex items-center justify-between">
        <Link to="/" className="inline-flex items-center gap-2 text-foreground font-semibold">
          <span className="inline-block h-2 w-2 rounded-full bg-primary" />
          <span>Vaanika</span>
        </Link>

        <div className="flex items-center gap-2">
          {isSignedIn ? (
            <Button variant="ghost" size="icon" aria-label="Notifications">
              <Bell className="h-5 w-5" />
            </Button>
          ) : (
            <Button asChild>
              <Link to="/signup">Sign up</Link>
            </Button>
          )}
        </div>
      </div>
    </nav>
  );
}
