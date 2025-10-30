import { cn } from "@/lib/utils";
import { ReactNode } from "react";

interface GradientCardProps {
  children: ReactNode;
  className?: string;
  variant?: "peach" | "purple" | "sky";
}

export const GradientCard = ({ children, className, variant = "peach" }: GradientCardProps) => {
  const gradientClass = {
    peach: "bg-gradient-peach",
    purple: "bg-gradient-purple",
    sky: "bg-gradient-sky",
  }[variant];

  return (
    <div
      className={cn(
        "rounded-3xl p-8 shadow-soft transition-all duration-300 hover:shadow-medium",
        gradientClass,
        className
      )}
    >
      {children}
    </div>
  );
};
