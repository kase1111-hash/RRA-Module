'use client';

import { cn } from '@/lib/utils';
import { Check } from 'lucide-react';

export interface ProgressProps {
  value: number;
  max?: number;
  size?: 'sm' | 'md' | 'lg';
  variant?: 'default' | 'success' | 'warning' | 'danger' | 'gradient';
  showLabel?: boolean;
  label?: string;
  animated?: boolean;
  className?: string;
}

const heights = {
  sm: 'h-1.5',
  md: 'h-2.5',
  lg: 'h-4',
};

const variants = {
  default: 'bg-primary-600 dark:bg-primary-500',
  success: 'bg-green-500',
  warning: 'bg-yellow-500',
  danger: 'bg-red-500',
  gradient: 'bg-gradient-to-r from-primary-500 via-purple-500 to-pink-500',
};

export function Progress({
  value,
  max = 100,
  size = 'md',
  variant = 'default',
  showLabel = false,
  label,
  animated = false,
  className,
}: ProgressProps) {
  const percentage = Math.min(100, Math.max(0, (value / max) * 100));

  return (
    <div className={cn('w-full', className)}>
      {(showLabel || label) && (
        <div className="flex justify-between mb-1.5 text-sm">
          <span className="text-gray-600 dark:text-gray-400">{label}</span>
          {showLabel && (
            <span className="font-medium text-gray-900 dark:text-white">
              {percentage.toFixed(0)}%
            </span>
          )}
        </div>
      )}
      <div
        className={cn(
          'w-full rounded-full bg-gray-200 dark:bg-gray-700 overflow-hidden',
          heights[size]
        )}
      >
        <div
          className={cn(
            'h-full rounded-full transition-all duration-500 ease-out',
            variants[variant],
            animated && 'animate-pulse'
          )}
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  );
}

// Step Progress for multi-step flows
export interface StepProgressProps {
  steps: string[];
  currentStep: number;
  variant?: 'default' | 'numbered' | 'dots';
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

const stepSizes = {
  sm: { circle: 'h-6 w-6 text-xs', line: 'h-0.5' },
  md: { circle: 'h-8 w-8 text-sm', line: 'h-1' },
  lg: { circle: 'h-10 w-10 text-base', line: 'h-1' },
};

export function StepProgress({
  steps,
  currentStep,
  variant = 'default',
  size = 'md',
  className,
}: StepProgressProps) {
  const sizeConfig = stepSizes[size];

  return (
    <div className={cn('w-full', className)}>
      <div className="flex items-center justify-between">
        {steps.map((step, index) => {
          const isCompleted = index < currentStep;
          const isCurrent = index === currentStep;
          const isLast = index === steps.length - 1;

          return (
            <div key={index} className={cn('flex items-center', !isLast && 'flex-1')}>
              {/* Step Circle */}
              <div className="flex flex-col items-center">
                <div
                  className={cn(
                    'flex items-center justify-center rounded-full font-medium transition-all duration-300',
                    sizeConfig.circle,
                    isCompleted &&
                      'bg-green-500 text-white',
                    isCurrent &&
                      'bg-primary-600 text-white ring-4 ring-primary-100 dark:ring-primary-900',
                    !isCompleted &&
                      !isCurrent &&
                      'bg-gray-200 text-gray-500 dark:bg-gray-700 dark:text-gray-400'
                  )}
                >
                  {isCompleted ? (
                    <Check className="h-4 w-4" />
                  ) : variant === 'numbered' ? (
                    index + 1
                  ) : variant === 'dots' ? (
                    <span className="h-2 w-2 rounded-full bg-current" />
                  ) : (
                    index + 1
                  )}
                </div>
                {/* Step Label */}
                <span
                  className={cn(
                    'mt-2 text-xs font-medium text-center max-w-[80px] hidden sm:block',
                    isCurrent
                      ? 'text-primary-600 dark:text-primary-400'
                      : isCompleted
                      ? 'text-green-600 dark:text-green-400'
                      : 'text-gray-500 dark:text-gray-400'
                  )}
                >
                  {step}
                </span>
              </div>

              {/* Connector Line */}
              {!isLast && (
                <div
                  className={cn(
                    'flex-1 mx-2 rounded-full transition-all duration-300',
                    sizeConfig.line,
                    isCompleted
                      ? 'bg-green-500'
                      : 'bg-gray-200 dark:bg-gray-700'
                  )}
                />
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

// Circular Progress
export interface CircularProgressProps {
  value: number;
  max?: number;
  size?: number;
  strokeWidth?: number;
  variant?: 'default' | 'success' | 'warning' | 'danger';
  showValue?: boolean;
  label?: string;
  className?: string;
}

const circularColors = {
  default: { stroke: '#0ea5e9', bg: '#e5e7eb' },
  success: { stroke: '#22c55e', bg: '#dcfce7' },
  warning: { stroke: '#eab308', bg: '#fef9c3' },
  danger: { stroke: '#ef4444', bg: '#fee2e2' },
};

export function CircularProgress({
  value,
  max = 100,
  size = 80,
  strokeWidth = 8,
  variant = 'default',
  showValue = true,
  label,
  className,
}: CircularProgressProps) {
  const percentage = Math.min(100, Math.max(0, (value / max) * 100));
  const radius = (size - strokeWidth) / 2;
  const circumference = radius * 2 * Math.PI;
  const offset = circumference - (percentage / 100) * circumference;
  const colors = circularColors[variant];

  return (
    <div className={cn('relative inline-flex items-center justify-center', className)}>
      <svg width={size} height={size} className="-rotate-90">
        {/* Background circle */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={colors.bg}
          strokeWidth={strokeWidth}
          className="dark:opacity-30"
        />
        {/* Progress circle */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={colors.stroke}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          className="transition-all duration-500 ease-out"
        />
      </svg>
      {/* Center content */}
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        {showValue && (
          <span className="text-lg font-bold text-gray-900 dark:text-white">
            {percentage.toFixed(0)}%
          </span>
        )}
        {label && (
          <span className="text-xs text-gray-500 dark:text-gray-400">{label}</span>
        )}
      </div>
    </div>
  );
}
