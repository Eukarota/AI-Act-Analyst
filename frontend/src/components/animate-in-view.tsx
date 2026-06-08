"use client";

import { motion, type MotionProps } from "framer-motion";
import { ReactNode } from "react";

interface Props extends MotionProps {
  children: ReactNode;
  delay?: number;
  className?: string;
}

export function AnimateInView({ children, delay = 0, className, ...rest }: Props) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-40px" }}
      transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1], delay }}
      className={className}
      {...rest}
    >
      {children}
    </motion.div>
  );
}
