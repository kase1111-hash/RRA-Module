'use client';

import { forwardRef, type HTMLAttributes, type ReactNode } from 'react';
import { cn } from '@/lib/utils';

export interface CardProps extends HTMLAttributes<HTMLDivElement> {
  variant?: 'default' | 'elevated' | 'outlined' | 'ghost';
  padding?: 'none' | 'sm' | 'md' | 'lg';
  hoverable?: boolean;
  interactive?: boolean;
}

const variants = {
  default: 'bg-white border border-gray-200 dark:bg-gray-800 dark:border-gray-700',
  elevated: 'bg-white shadow-lg border-0 dark:bg-gray-800',
  outlined: 'bg-transparent border-2 border-gray-200 dark:border-gray-700',
  ghost: 'bg-gray-50 border-0 dark:bg-gray-800/50',
};

const paddings = {
  none: '',
  sm: 'p-4',
  md: 'p-6',
  lg: 'p-8',
};

export const Card = forwardRef<HTMLDivElement, CardProps>(
  (
    {
      className,
      variant = 'default',
      padding = 'md',
      hoverable = false,
      interactive = false,
      children,
      ...props
    },
    ref
  ) => {
    return (
      <div
        ref={ref}
        className={cn(
          'rounded-xl transition-all duration-200',
          variants[variant],
          paddings[padding],
          hoverable && 'hover:shadow-lg hover:border-gray-300 dark:hover:border-gray-600',
          interactive && 'cursor-pointer active:scale-[0.99]',
          className
        )}
        {...props}
      >
        {children}
      </div>
    );
  }
);

Card.displayName = 'Card';

// Card sub-components
export interface CardHeaderProps extends HTMLAttributes<HTMLDivElement> {
  title?: ReactNode;
  subtitle?: ReactNode;
  action?: ReactNode;
}

export function CardHeader({ className, title, subtitle, action, children, ...props }: CardHeaderProps) {
  if (children) {
    return (
      <div className={cn('mb-4', className)} {...props}>
        {children}
      </div>
    );
  }

  return (
    <div className={cn('flex items-start justify-between mb-4', className)} {...props}>
      <div>
        {title && <h3 className="text-lg font-semibold text-gray-900 dark:text-white">{title}</h3>}
        {subtitle && <p className="text-sm text-gray-500 dark:text-gray-400 mt-0.5">{subtitle}</p>}
      </div>
      {action && <div>{action}</div>}
    </div>
  );
}

export interface CardContentProps extends HTMLAttributes<HTMLDivElement> {}

export function CardContent({ className, children, ...props }: CardContentProps) {
  return (
    <div className={cn('', className)} {...props}>
      {children}
    </div>
  );
}

export interface CardFooterProps extends HTMLAttributes<HTMLDivElement> {
  bordered?: boolean;
}

export function CardFooter({ className, bordered = true, children, ...props }: CardFooterProps) {
  return (
    <div
      className={cn(
        'mt-4 pt-4 flex items-center justify-between',
        bordered && 'border-t border-gray-100 dark:border-gray-700',
        className
      )}
      {...props}
    >
      {children}
    </div>
  );
}
