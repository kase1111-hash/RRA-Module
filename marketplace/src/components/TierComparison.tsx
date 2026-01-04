'use client';

import { useState } from 'react';
import { Check, X, Star, Zap, Building2, HelpCircle, ChevronDown, ChevronUp } from 'lucide-react';
import { cn, formatPrice } from '@/lib/utils';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import type { LicenseTier } from '@/types';

interface TierComparisonProps {
  tiers: LicenseTier[];
  basePrice: number;
  currency?: string;
  onSelectTier: (tier: LicenseTier) => void;
  selectedTierId?: string;
  highlightedTierId?: string;
}

interface Feature {
  name: string;
  description?: string;
  standard: boolean | string;
  premium: boolean | string;
  enterprise: boolean | string;
}

const DEFAULT_FEATURES: Feature[] = [
  { name: 'Source code access', standard: true, premium: true, enterprise: true },
  { name: 'Commercial use', standard: true, premium: true, enterprise: true },
  { name: 'Production deployment', standard: '1 project', premium: 'Unlimited', enterprise: 'Unlimited' },
  { name: 'Support response time', standard: '72 hours', premium: '24 hours', enterprise: '4 hours' },
  { name: 'Custom modifications', standard: false, premium: true, enterprise: true },
  { name: 'White-label rights', standard: false, premium: false, enterprise: true },
  { name: 'Priority bug fixes', standard: false, premium: true, enterprise: true },
  { name: 'Feature requests', standard: false, premium: 'Considered', enterprise: 'Priority' },
  { name: 'License transfers', standard: false, premium: true, enterprise: true },
  { name: 'Competing use', standard: false, premium: false, enterprise: 'Limited' },
];

const TIER_ICONS = {
  standard: Star,
  premium: Zap,
  enterprise: Building2,
};

const TIER_COLORS = {
  standard: {
    bg: 'bg-gray-50 dark:bg-gray-800',
    border: 'border-gray-200 dark:border-gray-700',
    badge: 'default' as const,
    button: 'secondary' as const,
  },
  premium: {
    bg: 'bg-primary-50 dark:bg-primary-900/20',
    border: 'border-primary-200 dark:border-primary-800 ring-2 ring-primary-100 dark:ring-primary-900',
    badge: 'primary' as const,
    button: 'primary' as const,
  },
  enterprise: {
    bg: 'bg-purple-50 dark:bg-purple-900/20',
    border: 'border-purple-200 dark:border-purple-800',
    badge: 'info' as const,
    button: 'outline' as const,
  },
};

export function TierComparison({
  tiers,
  basePrice,
  currency = 'ETH',
  onSelectTier,
  selectedTierId,
  highlightedTierId = 'premium',
}: TierComparisonProps) {
  const [expandedFeatures, setExpandedFeatures] = useState(false);
  const [hoveredTier, setHoveredTier] = useState<string | null>(null);

  const tierMap = tiers.reduce((acc, tier) => {
    acc[tier.id] = tier;
    return acc;
  }, {} as Record<string, LicenseTier>);

  const getPrice = (multiplier: number) => {
    return formatPrice(basePrice * multiplier, currency);
  };

  const renderFeatureValue = (value: boolean | string) => {
    if (typeof value === 'boolean') {
      return value ? (
        <Check className="h-5 w-5 text-green-500 mx-auto" />
      ) : (
        <X className="h-5 w-5 text-gray-300 dark:text-gray-600 mx-auto" />
      );
    }
    return <span className="text-sm font-medium text-gray-900 dark:text-white">{value}</span>;
  };

  const displayedFeatures = expandedFeatures ? DEFAULT_FEATURES : DEFAULT_FEATURES.slice(0, 5);

  return (
    <div className="w-full">
      {/* Tier Cards (Mobile & Desktop) */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
        {['standard', 'premium', 'enterprise'].map((tierId) => {
          const tier = tierMap[tierId];
          const colors = TIER_COLORS[tierId as keyof typeof TIER_COLORS];
          const Icon = TIER_ICONS[tierId as keyof typeof TIER_ICONS];
          const isHighlighted = tierId === highlightedTierId;
          const isSelected = tierId === selectedTierId;
          const isHovered = tierId === hoveredTier;
          const multiplier = tierId === 'standard' ? 1 : tierId === 'premium' ? 2.5 : 5;

          return (
            <div
              key={tierId}
              onMouseEnter={() => setHoveredTier(tierId)}
              onMouseLeave={() => setHoveredTier(null)}
              className={cn(
                'relative rounded-xl border-2 p-6 transition-all duration-200',
                colors.bg,
                colors.border,
                isHovered && 'shadow-lg transform -translate-y-1',
                isSelected && 'ring-2 ring-offset-2 ring-primary-500'
              )}
            >
              {/* Popular Badge */}
              {isHighlighted && (
                <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                  <Badge variant="primary" size="md">
                    <Star className="h-3 w-3 mr-1" />
                    Most Popular
                  </Badge>
                </div>
              )}

              {/* Header */}
              <div className="text-center mb-6">
                <div className={cn(
                  'inline-flex items-center justify-center h-12 w-12 rounded-full mb-3',
                  tierId === 'standard' && 'bg-gray-200 dark:bg-gray-700',
                  tierId === 'premium' && 'bg-primary-100 dark:bg-primary-900',
                  tierId === 'enterprise' && 'bg-purple-100 dark:bg-purple-900'
                )}>
                  <Icon className={cn(
                    'h-6 w-6',
                    tierId === 'standard' && 'text-gray-600 dark:text-gray-400',
                    tierId === 'premium' && 'text-primary-600 dark:text-primary-400',
                    tierId === 'enterprise' && 'text-purple-600 dark:text-purple-400'
                  )} />
                </div>
                <h3 className="text-xl font-bold text-gray-900 dark:text-white capitalize">
                  {tierId}
                </h3>
                <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                  {tierId === 'standard' && 'For individuals & small projects'}
                  {tierId === 'premium' && 'For growing teams & startups'}
                  {tierId === 'enterprise' && 'For large organizations'}
                </p>
              </div>

              {/* Price */}
              <div className="text-center mb-6">
                <div className="flex items-baseline justify-center gap-1">
                  <span className="text-3xl font-bold text-gray-900 dark:text-white">
                    {getPrice(multiplier)}
                  </span>
                </div>
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                  One-time payment
                </p>
                {isHighlighted && (
                  <p className="text-xs text-green-600 dark:text-green-400 mt-1 font-medium">
                    Best value for most users
                  </p>
                )}
              </div>

              {/* Key Features */}
              <ul className="space-y-3 mb-6">
                {tier?.features?.slice(0, 4).map((feature, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm">
                    <Check className="h-4 w-4 text-green-500 shrink-0 mt-0.5" />
                    <span className="text-gray-700 dark:text-gray-300">{feature}</span>
                  </li>
                )) || (
                  <>
                    <li className="flex items-start gap-2 text-sm">
                      <Check className="h-4 w-4 text-green-500 shrink-0 mt-0.5" />
                      <span className="text-gray-700 dark:text-gray-300">Full source code access</span>
                    </li>
                    <li className="flex items-start gap-2 text-sm">
                      <Check className="h-4 w-4 text-green-500 shrink-0 mt-0.5" />
                      <span className="text-gray-700 dark:text-gray-300">Commercial use rights</span>
                    </li>
                    <li className="flex items-start gap-2 text-sm">
                      <Check className="h-4 w-4 text-green-500 shrink-0 mt-0.5" />
                      <span className="text-gray-700 dark:text-gray-300">
                        {tierId === 'standard' ? '12 months updates' : 'Lifetime updates'}
                      </span>
                    </li>
                  </>
                )}
              </ul>

              {/* CTA Button */}
              <Button
                variant={colors.button}
                fullWidth
                onClick={() => onSelectTier(tier || { id: tierId, name: tierId, price_multiplier: multiplier, features: [] })}
                className={isSelected ? 'ring-2 ring-offset-2 ring-primary-500' : ''}
              >
                {isSelected ? 'Selected' : `Choose ${tierId.charAt(0).toUpperCase() + tierId.slice(1)}`}
              </Button>
            </div>
          );
        })}
      </div>

      {/* Detailed Comparison Table */}
      <div className="rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
        <div className="bg-gray-50 dark:bg-gray-800 px-6 py-4 border-b border-gray-200 dark:border-gray-700">
          <h4 className="font-semibold text-gray-900 dark:text-white">
            Detailed Feature Comparison
          </h4>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-200 dark:border-gray-700">
                <th className="text-left py-3 px-6 text-sm font-medium text-gray-500 dark:text-gray-400">
                  Feature
                </th>
                <th className="text-center py-3 px-4 text-sm font-medium text-gray-500 dark:text-gray-400 w-32">
                  Standard
                </th>
                <th className="text-center py-3 px-4 text-sm font-medium text-gray-500 dark:text-gray-400 w-32 bg-primary-50/50 dark:bg-primary-900/10">
                  Premium
                </th>
                <th className="text-center py-3 px-4 text-sm font-medium text-gray-500 dark:text-gray-400 w-32">
                  Enterprise
                </th>
              </tr>
            </thead>
            <tbody>
              {displayedFeatures.map((feature, index) => (
                <tr
                  key={index}
                  className={cn(
                    'border-b border-gray-100 dark:border-gray-800',
                    index % 2 === 0 && 'bg-gray-50/50 dark:bg-gray-800/50'
                  )}
                >
                  <td className="py-3 px-6">
                    <div className="flex items-center gap-2">
                      <span className="text-sm text-gray-900 dark:text-white">{feature.name}</span>
                      {feature.description && (
                        <button className="text-gray-400 hover:text-gray-600">
                          <HelpCircle className="h-4 w-4" />
                        </button>
                      )}
                    </div>
                  </td>
                  <td className="text-center py-3 px-4">
                    {renderFeatureValue(feature.standard)}
                  </td>
                  <td className="text-center py-3 px-4 bg-primary-50/50 dark:bg-primary-900/10">
                    {renderFeatureValue(feature.premium)}
                  </td>
                  <td className="text-center py-3 px-4">
                    {renderFeatureValue(feature.enterprise)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Show More/Less */}
        {DEFAULT_FEATURES.length > 5 && (
          <div className="px-6 py-3 border-t border-gray-200 dark:border-gray-700">
            <button
              onClick={() => setExpandedFeatures(!expandedFeatures)}
              className="flex items-center gap-1 text-sm text-primary-600 hover:text-primary-700 dark:text-primary-400 font-medium"
            >
              {expandedFeatures ? (
                <>
                  Show less <ChevronUp className="h-4 w-4" />
                </>
              ) : (
                <>
                  Show all {DEFAULT_FEATURES.length} features <ChevronDown className="h-4 w-4" />
                </>
              )}
            </button>
          </div>
        )}
      </div>

      {/* Help Section */}
      <div className="mt-6 rounded-lg bg-gray-50 dark:bg-gray-800 p-4 text-center">
        <p className="text-sm text-gray-600 dark:text-gray-400">
          Not sure which tier is right for you?{' '}
          <button className="text-primary-600 hover:text-primary-700 dark:text-primary-400 font-medium">
            Chat with our advisor
          </button>{' '}
          to discuss your specific needs.
        </p>
      </div>
    </div>
  );
}
