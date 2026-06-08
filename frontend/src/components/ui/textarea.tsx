import * as React from "react";
import { cn } from "@/lib/utils";

export type TextareaProps = React.TextareaHTMLAttributes<HTMLTextAreaElement>;

export const Textarea = React.forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ className, ...props }, ref) => {
    return (
      <textarea
        ref={ref}
        className={cn(
          "w-full rounded-xl bg-white/[0.025] ring-1 ring-white/[0.06]",
          "px-4 py-3 text-sm leading-relaxed text-foreground placeholder:text-foreground-dim",
          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/20",
          "transition-shadow scrollbar-thin",
          className,
        )}
        {...props}
      />
    );
  },
);
Textarea.displayName = "Textarea";
