'use client';

import { useState, useCallback } from 'react';
import type { FullVerificationResponse, PurchaseLink, VerificationResult } from '@/types';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface UseVerificationOptions {
  skipTests?: boolean;
  skipSecurity?: boolean;
  network?: 'mainnet' | 'testnet' | 'localhost';
}

interface VerifyRequestParams {
  repoUrl: string;
  ownerAddress?: string;
  options?: UseVerificationOptions;
}

interface UseVerificationReturn {
  verify: (params: VerifyRequestParams) => Promise<FullVerificationResponse | null>;
  getStatus: (repoId: string) => Promise<FullVerificationResponse | null>;
  isLoading: boolean;
  error: string | null;
  data: FullVerificationResponse | null;
}

/**
 * Hook for verifying repositories through the RRA API
 */
export function useVerification(): UseVerificationReturn {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<FullVerificationResponse | null>(null);

  const verify = useCallback(async (params: VerifyRequestParams): Promise<FullVerificationResponse | null> => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch(`${API_BASE_URL}/api/verify/check`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': process.env.NEXT_PUBLIC_API_KEY || '',
        },
        body: JSON.stringify({
          repo_url: params.repoUrl,
          owner_address: params.ownerAddress,
          network: params.options?.network || 'testnet',
          skip_tests: params.options?.skipTests || false,
          skip_security: params.options?.skipSecurity || false,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `Verification failed: ${response.status}`);
      }

      const result = await response.json();
      setData(result);
      return result;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Verification failed';
      setError(errorMessage);
      return null;
    } finally {
      setIsLoading(false);
    }
  }, []);

  const getStatus = useCallback(async (repoId: string): Promise<FullVerificationResponse | null> => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch(`${API_BASE_URL}/api/verify/status/${encodeURIComponent(repoId)}`, {
        headers: {
          'X-API-Key': process.env.NEXT_PUBLIC_API_KEY || '',
        },
      });

      if (!response.ok) {
        if (response.status === 404) {
          return null;
        }
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `Failed to get status: ${response.status}`);
      }

      const result = await response.json();
      setData(result);
      return result;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to get verification status';
      setError(errorMessage);
      return null;
    } finally {
      setIsLoading(false);
    }
  }, []);

  return {
    verify,
    getStatus,
    isLoading,
    error,
    data,
  };
}

interface UsePurchaseLinksOptions {
  network?: 'mainnet' | 'testnet' | 'localhost';
}

interface UsePurchaseLinksReturn {
  getLinks: (repoId: string, ownerAddress: string, options?: UsePurchaseLinksOptions) => Promise<PurchaseLink[] | null>;
  isLoading: boolean;
  error: string | null;
  links: PurchaseLink[] | null;
}

/**
 * Hook for generating blockchain purchase links
 */
export function usePurchaseLinks(): UsePurchaseLinksReturn {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [links, setLinks] = useState<PurchaseLink[] | null>(null);

  const getLinks = useCallback(async (
    repoId: string,
    ownerAddress: string,
    options?: UsePurchaseLinksOptions
  ): Promise<PurchaseLink[] | null> => {
    setIsLoading(true);
    setError(null);

    try {
      const params = new URLSearchParams({
        owner_address: ownerAddress,
        network: options?.network || 'testnet',
      });

      const response = await fetch(
        `${API_BASE_URL}/api/verify/purchase-links/${encodeURIComponent(repoId)}?${params}`,
        {
          headers: {
            'X-API-Key': process.env.NEXT_PUBLIC_API_KEY || '',
          },
        }
      );

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `Failed to get purchase links: ${response.status}`);
      }

      const result = await response.json();
      setLinks(result);
      return result;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to get purchase links';
      setError(errorMessage);
      return null;
    } finally {
      setIsLoading(false);
    }
  }, []);

  return {
    getLinks,
    isLoading,
    error,
    links,
  };
}

interface UseExplorerLinkReturn {
  getExplorerLinks: (ipAssetId: string, network?: string) => Promise<{
    explorer_url: string;
    view_link: string;
    purchase_link: string;
    network: string;
  } | null>;
  isLoading: boolean;
  error: string | null;
}

/**
 * Hook for getting Story Protocol explorer links
 */
export function useExplorerLinks(): UseExplorerLinkReturn {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const getExplorerLinks = useCallback(async (
    ipAssetId: string,
    network: string = 'testnet'
  ) => {
    setIsLoading(true);
    setError(null);

    try {
      const params = new URLSearchParams({ network });
      const response = await fetch(
        `${API_BASE_URL}/api/verify/explorer-link/${encodeURIComponent(ipAssetId)}?${params}`,
        {
          headers: {
            'X-API-Key': process.env.NEXT_PUBLIC_API_KEY || '',
          },
        }
      );

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `Failed to get explorer links: ${response.status}`);
      }

      return await response.json();
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to get explorer links';
      setError(errorMessage);
      return null;
    } finally {
      setIsLoading(false);
    }
  }, []);

  return {
    getExplorerLinks,
    isLoading,
    error,
  };
}

interface UseCategorizeReturn {
  categorize: (repoUrl: string) => Promise<{
    primary_category: string;
    subcategory: string | null;
    confidence: number;
    tags: string[];
    technologies: string[];
    frameworks: string[];
  } | null>;
  isLoading: boolean;
  error: string | null;
}

/**
 * Hook for categorizing repositories
 */
export function useCategorize(): UseCategorizeReturn {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const categorize = useCallback(async (repoUrl: string) => {
    setIsLoading(true);
    setError(null);

    try {
      const params = new URLSearchParams({ repo_url: repoUrl });
      const response = await fetch(`${API_BASE_URL}/api/verify/categorize?${params}`, {
        method: 'POST',
        headers: {
          'X-API-Key': process.env.NEXT_PUBLIC_API_KEY || '',
        },
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `Categorization failed: ${response.status}`);
      }

      return await response.json();
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Categorization failed';
      setError(errorMessage);
      return null;
    } finally {
      setIsLoading(false);
    }
  }, []);

  return {
    categorize,
    isLoading,
    error,
  };
}

interface UseEmbedWidgetReturn {
  getWidget: (repoId: string, ownerAddress: string, options?: { network?: string; theme?: string }) => Promise<{
    html: string;
    repo_url: string;
    ip_asset_id: string;
  } | null>;
  isLoading: boolean;
  error: string | null;
}

/**
 * Hook for generating embeddable widgets
 */
export function useEmbedWidget(): UseEmbedWidgetReturn {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const getWidget = useCallback(async (
    repoId: string,
    ownerAddress: string,
    options?: { network?: string; theme?: string }
  ) => {
    setIsLoading(true);
    setError(null);

    try {
      const params = new URLSearchParams({
        owner_address: ownerAddress,
        network: options?.network || 'testnet',
        theme: options?.theme || 'light',
      });

      const response = await fetch(
        `${API_BASE_URL}/api/verify/widget/${encodeURIComponent(repoId)}?${params}`,
        {
          headers: {
            'X-API-Key': process.env.NEXT_PUBLIC_API_KEY || '',
          },
        }
      );

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `Failed to get widget: ${response.status}`);
      }

      return await response.json();
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to get widget';
      setError(errorMessage);
      return null;
    } finally {
      setIsLoading(false);
    }
  }, []);

  return {
    getWidget,
    isLoading,
    error,
  };
}
