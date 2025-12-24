// Repository and Agent Types

export interface Repository {
  id: string;
  url: string;
  name: string;
  owner: string;
  description: string;
  kb_path: string;
  updated_at: string;
  languages: string[];
  files: number;
  stars?: number;
  forks?: number;
}

export interface MarketConfig {
  license_identifier: string;
  license_model: string;
  target_price: string;
  floor_price: string;
  negotiation_style: string;
  features: string[];
  developer_wallet?: string;
  copyright_holder?: string;
}

export interface AgentDetails {
  repository: Repository;
  market_config: MarketConfig;
  statistics: {
    code_files: number;
    languages: string[];
    total_lines: number;
    test_coverage?: number;
  };
  reputation: {
    score: number;
    total_sales: number;
    total_revenue: string;
  };
}

export interface AgentStats {
  total_sales: number;
  total_revenue: string;
  average_price: string;
  reputation_score: number;
  active_negotiations: number;
}

// Negotiation Types

export type NegotiationPhase =
  | 'greeting'
  | 'discovery'
  | 'proposal'
  | 'negotiation'
  | 'closing'
  | 'completed';

export interface NegotiationMessage {
  id: string;
  role: 'agent' | 'buyer';
  content: string;
  timestamp: string;
}

export interface NegotiationSession {
  session_id: string;
  repo_id: string;
  phase: NegotiationPhase;
  messages: NegotiationMessage[];
  created_at: string;
  updated_at: string;
  final_offer?: {
    price: string;
    license_tier: string;
    terms: string[];
  };
}

// License Types

export interface LicenseTier {
  id: string;
  name: string;
  price: string;
  features: string[];
  duration: string;
  seats: number;
}

export interface LicenseNFT {
  token_id: number;
  owner_address: string;
  repo_url: string;
  license_tier: string;
  purchased_at: string;
  expires_at?: string;
  metadata: {
    permitted_uses: string[];
    restrictions: string[];
  };
}

// Search and Filter Types

export interface SearchFilters {
  query?: string;
  language?: string;
  category?: string;
  price_min?: number;
  price_max?: number;
  sort_by?: 'recent' | 'popular' | 'price_low' | 'price_high';
}

export interface SearchResult {
  repositories: Repository[];
  total: number;
  page: number;
  per_page: number;
}

// WebSocket Types

export interface WSMessage {
  type: 'message' | 'typing' | 'phase_change' | 'offer' | 'error';
  payload: unknown;
  timestamp: string;
}

export interface WSChatMessage extends WSMessage {
  type: 'message';
  payload: {
    role: 'agent' | 'buyer';
    content: string;
  };
}

export interface WSTypingMessage extends WSMessage {
  type: 'typing';
  payload: {
    is_typing: boolean;
  };
}

// Verification Types

export type VerificationStatus = 'passed' | 'warning' | 'failed' | 'skipped';

export interface VerificationCheck {
  name: string;
  status: VerificationStatus;
  message: string;
  details?: Record<string, unknown>;
}

export interface VerificationResult {
  repo_url: string;
  overall_status: VerificationStatus;
  score: number;
  checks: VerificationCheck[];
  verified_at: string;
}

export interface ReadmeMetadata {
  title: string;
  description: string;
  short_description: string;
  features: string[];
  technologies: string[];
  has_examples: boolean;
  has_api_docs: boolean;
}

export interface CategoryResult {
  primary_category: string;
  subcategory?: string;
  confidence: number;
  tags: string[];
  technologies: string[];
  frameworks: string[];
}

// Blockchain / Purchase Link Types

export type NetworkType = 'mainnet' | 'testnet' | 'localhost';

export interface PurchaseLink {
  url: string;
  network: NetworkType;
  tier: string;
  price_display: string;
  ip_asset_id: string;
  license_terms_id?: string;
}

export interface MarketplaceListing {
  repo_url: string;
  repo_name: string;
  description: string;
  category: string;
  ip_asset_id: string;
  verification_score: number;
  purchase_links: PurchaseLink[];
  tags: string[];
  technologies: string[];
}

export interface FullVerificationResponse {
  verification: VerificationResult;
  category: CategoryResult;
  readme: ReadmeMetadata;
  marketplace?: MarketplaceListing;
}

// Extended Repository with Verification

export interface RepositoryWithVerification extends Repository {
  verification?: VerificationResult;
  category?: CategoryResult;
  blockchain_links?: MarketplaceListing;
}

// Extended Agent Details with Verification

export interface AgentDetailsWithVerification extends AgentDetails {
  verification?: VerificationResult;
  category?: CategoryResult;
  readme_metadata?: ReadmeMetadata;
  blockchain_links?: MarketplaceListing;
}

