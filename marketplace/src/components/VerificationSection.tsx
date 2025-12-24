'use client';

import { useState } from 'react';
import {
  Shield,
  ShieldCheck,
  ShieldAlert,
  ShieldX,
  ChevronDown,
  ChevronUp,
  TestTube,
  Lock,
  FileCode,
  FileText,
  Scale,
  BookOpen,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  MinusCircle,
} from 'lucide-react';
import { cn, getVerificationColor, getVerificationBgColor } from '@/lib/utils';
import { VerificationBadge, VerificationScore } from './VerificationBadge';
import type { VerificationResult, VerificationCheck, VerificationStatus } from '@/types';

interface VerificationSectionProps {
  verification: VerificationResult;
  className?: string;
  defaultExpanded?: boolean;
}

export function VerificationSection({
  verification,
  className,
  defaultExpanded = false,
}: VerificationSectionProps) {
  const [expanded, setExpanded] = useState(defaultExpanded);

  const getCheckIcon = (name: string) => {
    switch (name.toLowerCase()) {
      case 'tests':
        return TestTube;
      case 'security':
        return Lock;
      case 'linting':
        return FileCode;
      case 'build':
        return FileCode;
      case 'documentation':
        return BookOpen;
      case 'license':
        return Scale;
      case 'readme_alignment':
        return FileText;
      default:
        return Shield;
    }
  };

  const getStatusIcon = (status: VerificationStatus) => {
    switch (status) {
      case 'passed':
        return <CheckCircle2 size={16} className="text-green-500" />;
      case 'warning':
        return <AlertTriangle size={16} className="text-yellow-500" />;
      case 'failed':
        return <XCircle size={16} className="text-red-500" />;
      case 'skipped':
        return <MinusCircle size={16} className="text-gray-400" />;
      default:
        return <MinusCircle size={16} className="text-gray-400" />;
    }
  };

  const passedCount = verification.checks.filter(c => c.status === 'passed').length;
  const warningCount = verification.checks.filter(c => c.status === 'warning').length;
  const failedCount = verification.checks.filter(c => c.status === 'failed').length;

  return (
    <div className={cn('rounded-lg border border-gray-200 dark:border-gray-700', className)}>
      {/* Header */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between p-4 hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors"
      >
        <div className="flex items-center gap-4">
          <VerificationScore score={verification.score} size="sm" showLabel={false} />
          <div className="text-left">
            <div className="flex items-center gap-2">
              <h3 className="font-semibold text-gray-900 dark:text-white">
                Code Verification
              </h3>
              <VerificationBadge status={verification.overall_status} size="sm" />
            </div>
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-0.5">
              {passedCount} passed, {warningCount} warnings, {failedCount} failed
            </p>
          </div>
        </div>
        {expanded ? (
          <ChevronUp size={20} className="text-gray-400" />
        ) : (
          <ChevronDown size={20} className="text-gray-400" />
        )}
      </button>

      {/* Expanded Content */}
      {expanded && (
        <div className="border-t border-gray-200 dark:border-gray-700 p-4 space-y-3">
          {verification.checks.map((check) => (
            <CheckItem key={check.name} check={check} getCheckIcon={getCheckIcon} getStatusIcon={getStatusIcon} />
          ))}

          <div className="pt-3 border-t border-gray-200 dark:border-gray-700 flex justify-between items-center text-xs text-gray-500">
            <span>Verified at: {new Date(verification.verified_at).toLocaleString()}</span>
            <span className="font-mono">{verification.repo_url.split('/').slice(-1)[0]}</span>
          </div>
        </div>
      )}
    </div>
  );
}

interface CheckItemProps {
  check: VerificationCheck;
  getCheckIcon: (name: string) => React.ComponentType<{ size?: number | string; className?: string }>;
  getStatusIcon: (status: VerificationStatus) => React.ReactNode;
}

function CheckItem({ check, getCheckIcon, getStatusIcon }: CheckItemProps) {
  const [showDetails, setShowDetails] = useState(false);
  const Icon = getCheckIcon(check.name);

  const formatCheckName = (name: string) => {
    return name.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
  };

  return (
    <div className="rounded-md border border-gray-100 dark:border-gray-800">
      <button
        onClick={() => check.details && setShowDetails(!showDetails)}
        className={cn(
          'w-full flex items-center justify-between p-3 text-left',
          check.details && 'hover:bg-gray-50 dark:hover:bg-gray-800/30 cursor-pointer'
        )}
      >
        <div className="flex items-center gap-3">
          <Icon size={18} className="text-gray-400" />
          <div>
            <div className="font-medium text-gray-900 dark:text-white text-sm">
              {formatCheckName(check.name)}
            </div>
            <div className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
              {check.message}
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {getStatusIcon(check.status)}
          {check.details && (
            showDetails ? (
              <ChevronUp size={14} className="text-gray-400" />
            ) : (
              <ChevronDown size={14} className="text-gray-400" />
            )
          )}
        </div>
      </button>

      {showDetails && check.details && (
        <div className="border-t border-gray-100 dark:border-gray-800 p-3 bg-gray-50 dark:bg-gray-800/20">
          <pre className="text-xs text-gray-600 dark:text-gray-400 whitespace-pre-wrap font-mono">
            {JSON.stringify(check.details, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}

interface VerificationSummaryProps {
  verification: VerificationResult;
  className?: string;
}

export function VerificationSummary({ verification, className }: VerificationSummaryProps) {
  return (
    <div className={cn('flex items-center gap-4 p-4 rounded-lg', getVerificationBgColor(verification.overall_status), className)}>
      <VerificationScore score={verification.score} size="md" showLabel={false} />
      <div>
        <div className="flex items-center gap-2">
          <span className="font-semibold text-gray-900 dark:text-white">
            Verification Score: {verification.score.toFixed(0)}/100
          </span>
          <VerificationBadge status={verification.overall_status} size="sm" />
        </div>
        <p className="text-sm text-gray-600 dark:text-gray-300 mt-1">
          {verification.checks.filter(c => c.status === 'passed').length} of {verification.checks.length} checks passed
        </p>
      </div>
    </div>
  );
}
