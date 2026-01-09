'use client';

import { useState, useEffect, useCallback } from 'react';
import { useAccount, useWriteContract, useWaitForTransactionReceipt, useSwitchChain, useChainId } from 'wagmi';
import { parseEther, formatEther, type Address } from 'viem';
import { ExternalLink, Loader2, Check, AlertCircle, Wallet, ArrowRight } from 'lucide-react';
import { ConnectButton } from '@rainbow-me/rainbowkit';
import { cn } from '@/lib/utils';

// Story Protocol Constants
const STORY_MAINNET_CHAIN_ID = 1514;
const STORY_TESTNET_CHAIN_ID = 1315;

// Story Protocol Contract Addresses (from deployment-1514.json and deployment-1315.json)
// See: https://docs.story.foundation/developers/deployed-smart-contracts
const STORY_CONTRACTS = {
  mainnet: {
    licensingModule: '0x04fbd8a2e56dd85CFD5500A4A4DfA955B9f1dE6f' as Address,
    pilTemplate: '0x2E896b0b2Fdb7457499B56AAaA4AE55BCB4Cd316' as Address,
    explorer: 'https://explorer.story.foundation',
  },
  testnet: {
    licensingModule: '0x5a7D9Fa17DE09350F481A53B470D798c1c1aabae' as Address,
    pilTemplate: '0x2E896b0b2Fdb7457499B56AAaA4AE55BCB4Cd316' as Address,
    explorer: 'https://aeneid.explorer.story.foundation',
  },
};

// Licensing Module ABI (minimal for mintLicenseTokens)
const LICENSING_MODULE_ABI = [
  {
    inputs: [
      { name: 'licensorIpId', type: 'address' },
      { name: 'licenseTemplate', type: 'address' },
      { name: 'licenseTermsId', type: 'uint256' },
      { name: 'amount', type: 'uint256' },
      { name: 'receiver', type: 'address' },
      { name: 'royaltyContext', type: 'bytes' },
    ],
    name: 'mintLicenseTokens',
    outputs: [{ name: '', type: 'uint256[]' }],
    stateMutability: 'payable',
    type: 'function',
  },
] as const;

interface StoryProtocolPurchaseProps {
  ipAssetId: Address;
  licenseTermsId: number;
  price: string; // e.g., "0.05 ETH"
  repoName: string;
  repoOwner: string;
  network?: 'mainnet' | 'testnet';
  onSuccess?: (txHash: string, tokenIds: bigint[]) => void;
  onError?: (error: Error) => void;
  className?: string;
}

type PurchaseStatus = 'idle' | 'switching-chain' | 'confirming' | 'pending' | 'success' | 'error';

export function StoryProtocolPurchase({
  ipAssetId,
  licenseTermsId,
  price,
  repoName,
  repoOwner,
  network = 'testnet',  // Default to Aeneid testnet
  onSuccess,
  onError,
  className,
}: StoryProtocolPurchaseProps) {
  const { address, isConnected } = useAccount();
  const currentChainId = useChainId();
  const { switchChain } = useSwitchChain();

  const [status, setStatus] = useState<PurchaseStatus>('idle');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const targetChainId = network === 'mainnet' ? STORY_MAINNET_CHAIN_ID : STORY_TESTNET_CHAIN_ID;
  const isCorrectChain = currentChainId === targetChainId;
  const contracts = STORY_CONTRACTS[network];

  // Parse price to wei
  const priceInWei = parseEther(price.replace(/\s*ETH\s*/i, ''));

  // Contract write hook
  const {
    writeContract,
    data: txHash,
    error: writeError,
    isPending: isWritePending,
  } = useWriteContract();

  // Transaction receipt hook
  const {
    isLoading: isConfirming,
    isSuccess: isConfirmed,
    data: receipt,
  } = useWaitForTransactionReceipt({
    hash: txHash,
  });

  // Handle chain switching
  const handleSwitchChain = useCallback(async () => {
    try {
      setStatus('switching-chain');
      setErrorMessage(null);
      await switchChain({ chainId: targetChainId });
    } catch (error) {
      setStatus('error');
      setErrorMessage('Failed to switch network. Please switch manually.');
    }
  }, [switchChain, targetChainId]);

  // Handle purchase
  const handlePurchase = useCallback(async () => {
    if (!address) return;

    try {
      setStatus('confirming');
      setErrorMessage(null);

      writeContract({
        address: contracts.licensingModule,
        abi: LICENSING_MODULE_ABI,
        functionName: 'mintLicenseTokens',
        args: [
          ipAssetId,
          contracts.pilTemplate,
          BigInt(licenseTermsId),
          BigInt(1), // amount
          address,
          '0x', // royaltyContext (empty bytes)
        ],
        value: priceInWei,
      });
    } catch (error) {
      setStatus('error');
      setErrorMessage(error instanceof Error ? error.message : 'Transaction failed');
      onError?.(error instanceof Error ? error : new Error('Transaction failed'));
    }
  }, [address, writeContract, contracts, ipAssetId, licenseTermsId, priceInWei, onError]);

  // Update status based on transaction state
  useEffect(() => {
    if (isWritePending) {
      setStatus('confirming');
    } else if (txHash && isConfirming) {
      setStatus('pending');
    } else if (isConfirmed && receipt) {
      setStatus('success');
      // Extract license token IDs from receipt events (if available)
      onSuccess?.(txHash!, []);
    } else if (writeError) {
      setStatus('error');
      setErrorMessage(writeError.message || 'Transaction failed');
      onError?.(writeError);
    }
  }, [isWritePending, txHash, isConfirming, isConfirmed, receipt, writeError, onSuccess, onError]);

  // Reset to chain switch state when chain changes
  useEffect(() => {
    if (status === 'switching-chain' && isCorrectChain) {
      setStatus('idle');
    }
  }, [isCorrectChain, status]);

  // Render based on connection state
  if (!isConnected) {
    return (
      <div className={cn('rounded-xl bg-gray-50 dark:bg-gray-800/50 p-6', className)}>
        <div className="text-center">
          <Wallet className="mx-auto h-12 w-12 text-gray-400 mb-4" />
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
            Connect Your Wallet
          </h3>
          <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
            Connect your wallet to purchase a license for {repoName}
          </p>
          <ConnectButton />
        </div>
      </div>
    );
  }

  // Render based on chain state
  if (!isCorrectChain) {
    return (
      <div className={cn('rounded-xl bg-gray-50 dark:bg-gray-800/50 p-6', className)}>
        <div className="text-center">
          <AlertCircle className="mx-auto h-12 w-12 text-amber-500 mb-4" />
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
            Wrong Network
          </h3>
          <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
            Please switch to Story Protocol {network === 'mainnet' ? 'Mainnet' : 'Testnet'}
          </p>
          <button
            onClick={handleSwitchChain}
            disabled={status === 'switching-chain'}
            className="inline-flex items-center justify-center gap-2 rounded-lg bg-indigo-600 px-6 py-3 text-sm font-semibold text-white hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {status === 'switching-chain' ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Switching...
              </>
            ) : (
              <>
                Switch Network
                <ArrowRight className="h-4 w-4" />
              </>
            )}
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className={cn('rounded-xl bg-white dark:bg-gray-800 shadow-sm', className)}>
      {/* Purchase Card */}
      <div className="p-6">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
              Purchase License
            </h3>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              {repoOwner}/{repoName}
            </p>
          </div>
          <div className="flex items-center gap-2 px-3 py-1 bg-green-100 dark:bg-green-900/30 rounded-full">
            <div className="h-2 w-2 rounded-full bg-green-500" />
            <span className="text-xs font-medium text-green-700 dark:text-green-300">
              Story Protocol
            </span>
          </div>
        </div>

        {/* Price Display */}
        <div className="mb-6 p-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
          <div className="flex items-center justify-between">
            <span className="text-gray-600 dark:text-gray-400">License Price</span>
            <div className="text-right">
              <p className="text-2xl font-bold text-gray-900 dark:text-white">{price}</p>
              <p className="text-xs text-gray-500">+ gas fees</p>
            </div>
          </div>
        </div>

        {/* Status Display */}
        {status === 'success' && (
          <div className="mb-6 p-4 bg-green-50 dark:bg-green-900/20 rounded-lg border border-green-200 dark:border-green-800">
            <div className="flex items-start gap-3">
              <Check className="h-5 w-5 text-green-500 mt-0.5" />
              <div className="flex-1">
                <p className="font-medium text-green-800 dark:text-green-300">
                  License Purchased Successfully!
                </p>
                <p className="text-sm text-green-700 dark:text-green-400 mt-1">
                  Your license NFT has been minted. You now have access to the repository.
                </p>
                {txHash && (
                  <a
                    href={`${contracts.explorer}/tx/${txHash}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 text-sm text-green-600 hover:underline mt-2"
                  >
                    View transaction <ExternalLink className="h-3 w-3" />
                  </a>
                )}
              </div>
            </div>
          </div>
        )}

        {status === 'error' && errorMessage && (
          <div className="mb-6 p-4 bg-red-50 dark:bg-red-900/20 rounded-lg border border-red-200 dark:border-red-800">
            <div className="flex items-start gap-3">
              <AlertCircle className="h-5 w-5 text-red-500 mt-0.5" />
              <div className="flex-1">
                <p className="font-medium text-red-800 dark:text-red-300">
                  Transaction Failed
                </p>
                <p className="text-sm text-red-700 dark:text-red-400 mt-1">
                  {errorMessage}
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Purchase Button */}
        <button
          onClick={handlePurchase}
          disabled={status === 'confirming' || status === 'pending' || status === 'success'}
          className={cn(
            'w-full rounded-lg py-4 text-lg font-semibold transition-all',
            status === 'success'
              ? 'bg-green-600 text-white cursor-not-allowed'
              : status === 'confirming' || status === 'pending'
              ? 'bg-indigo-400 text-white cursor-not-allowed'
              : 'bg-indigo-600 text-white hover:bg-indigo-700'
          )}
        >
          {status === 'confirming' ? (
            <span className="flex items-center justify-center gap-2">
              <Loader2 className="h-5 w-5 animate-spin" />
              Confirm in Wallet...
            </span>
          ) : status === 'pending' ? (
            <span className="flex items-center justify-center gap-2">
              <Loader2 className="h-5 w-5 animate-spin" />
              Processing...
            </span>
          ) : status === 'success' ? (
            <span className="flex items-center justify-center gap-2">
              <Check className="h-5 w-5" />
              License Purchased!
            </span>
          ) : (
            `Purchase License for ${price}`
          )}
        </button>

        {/* Info Footer */}
        <div className="mt-6 pt-6 border-t border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-between text-sm">
            <span className="text-gray-500 dark:text-gray-400">Network</span>
            <span className="font-medium text-gray-900 dark:text-white">
              Story Protocol {network === 'mainnet' ? 'Mainnet' : 'Testnet'}
            </span>
          </div>
          <div className="flex items-center justify-between text-sm mt-2">
            <span className="text-gray-500 dark:text-gray-400">IP Asset</span>
            <a
              href={`${contracts.explorer}/token/${ipAssetId}`}
              target="_blank"
              rel="noopener noreferrer"
              className="font-mono text-xs text-indigo-600 dark:text-indigo-400 hover:underline flex items-center gap-1"
            >
              {ipAssetId.slice(0, 6)}...{ipAssetId.slice(-4)}
              <ExternalLink className="h-3 w-3" />
            </a>
          </div>
          <div className="flex items-center justify-between text-sm mt-2">
            <span className="text-gray-500 dark:text-gray-400">License Terms ID</span>
            <span className="font-medium text-gray-900 dark:text-white">{licenseTermsId}</span>
          </div>
        </div>
      </div>
    </div>
  );
}

// Standalone purchase page component
interface StoryPurchasePageProps {
  ipAssetId: Address;
  licenseTermsId: number;
  repoName: string;
  repoOwner: string;
  price: string;
  features: string[];
  network?: 'mainnet' | 'testnet';
}

export function StoryPurchasePage({
  ipAssetId,
  licenseTermsId,
  repoName,
  repoOwner,
  price,
  features,
  network = 'testnet',  // Default to Aeneid testnet
}: StoryPurchasePageProps) {
  return (
    <div className="min-h-screen bg-gray-100 dark:bg-gray-900 py-12">
      <div className="max-w-lg mx-auto px-4">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">
            Purchase License
          </h1>
          <p className="text-gray-600 dark:text-gray-400">
            Powered by Story Protocol
          </p>
        </div>

        {/* License Details */}
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm mb-6 p-6">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">
            {repoOwner}/{repoName}
          </h2>
          <div className="space-y-2">
            <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300">
              Included Features:
            </h3>
            <ul className="space-y-1">
              {features.map((feature, index) => (
                <li key={index} className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400">
                  <Check className="h-4 w-4 text-green-500" />
                  {feature}
                </li>
              ))}
            </ul>
          </div>
        </div>

        {/* Purchase Component */}
        <StoryProtocolPurchase
          ipAssetId={ipAssetId}
          licenseTermsId={licenseTermsId}
          price={price}
          repoName={repoName}
          repoOwner={repoOwner}
          network={network}
          onSuccess={(txHash) => {
            console.log('Purchase successful:', txHash);
          }}
          onError={(error) => {
            console.error('Purchase failed:', error);
          }}
        />

        {/* Footer */}
        <div className="mt-8 text-center text-sm text-gray-500 dark:text-gray-400">
          <p>
            License NFT minted on{' '}
            <a
              href="https://story.foundation"
              target="_blank"
              rel="noopener noreferrer"
              className="text-indigo-600 dark:text-indigo-400 hover:underline"
            >
              Story Protocol
            </a>
          </p>
        </div>
      </div>
    </div>
  );
}

export default StoryProtocolPurchase;
