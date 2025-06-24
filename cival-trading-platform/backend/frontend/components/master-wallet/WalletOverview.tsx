/**
 * Master Wallet Overview Component
 * Phase 9: Complete wallet management with HD keys and multi-chain support
 */

import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Wallet,
  TrendingUp,
  TrendingDown,
  DollarSign,
  PieChart,
  Settings,
  Plus,
  Eye,
  EyeOff,
  RefreshCw,
  Activity,
  AlertTriangle,
  CheckCircle,
  Key,
  Shield,
  Link2,
  BarChart3,
  Zap,
  Target
} from 'lucide-react';

import { eventTransport, subscribe, emit, unsubscribe } from '../../ag-ui-setup/event-transport';

interface ChainBalance {
  chain_type: string;
  native_balance: number;
  token_balances: Record<string, number>;
  usd_value: number;
  last_updated: string;
}

interface PerformanceMetrics {
  total_trades: number;
  win_rate: number;
  total_pnl: number;
  total_pnl_percentage: number;
  max_drawdown: number;
  sharpe_ratio: number;
  performance_score: number;
}

interface WalletAllocation {
  wallet_id: string;
  allocation_amount: number;
  allocation_percentage: number;
  performance_score: number;
  last_rebalance: string;
}

interface MasterWalletData {
  master_wallet_id: string;
  name: string;
  description: string;
  total_balance_usd: number;
  total_allocated_amount: number;
  available_balance: number;
  allocation_efficiency: number;
  status: string;
  balances: Record<string, ChainBalance>;
  performance_metrics: PerformanceMetrics;
  current_allocations: WalletAllocation[];
  last_rebalance: string;
  created_at: string;
}

interface WalletOverviewProps {
  walletId?: string;
  onWalletSelect?: (walletId: string) => void;
  onCreateWallet?: () => void;
  className?: string;
}

const CHAIN_CONFIG = {
  ethereum: { name: 'Ethereum', symbol: 'ETH', color: 'bg-blue-500', icon: '⟠' },
  polygon: { name: 'Polygon', symbol: 'MATIC', color: 'bg-purple-500', icon: '⬟' },
  bsc: { name: 'BSC', symbol: 'BNB', color: 'bg-yellow-500', icon: '◆' },
  arbitrum: { name: 'Arbitrum', symbol: 'ETH', color: 'bg-blue-400', icon: '◢' },
  optimism: { name: 'Optimism', symbol: 'ETH', color: 'bg-red-500', icon: '○' },
  avalanche: { name: 'Avalanche', symbol: 'AVAX', color: 'bg-red-400', icon: '▲' }
};

export const WalletOverview: React.FC<WalletOverviewProps> = ({
  walletId,
  onWalletSelect,
  onCreateWallet,
  className = ''
}) => {
  const [walletData, setWalletData] = useState<MasterWalletData | null>(null);
  const [allWallets, setAllWallets] = useState<MasterWalletData[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [showBalances, setShowBalances] = useState(true);
  const [selectedChain, setSelectedChain] = useState<string>('all');
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [showAllocationModal, setShowAllocationModal] = useState(false);

  // Subscribe to wallet events
  useEffect(() => {
    const subscriptions = [
      subscribe('master_wallet.created', (data) => {
        console.log('🏦 Master wallet created:', data);
        loadWallets();
      }),

      subscribe('master_wallet.balances_updated', (data) => {
        if (data.wallet_id === walletId && walletId) {
          console.log('💰 Wallet balances updated:', data);
          loadWalletData(walletId);
        }
      }),

      subscribe('master_wallet.rebalanced', (data) => {
        if (data.wallet_id === walletId && walletId) {
          console.log('⚖️ Wallet rebalanced:', data);
          loadWalletData(walletId);
        }
      }),

      subscribe('hd_wallet_keys.generated', (data) => {
        if (data.wallet_id === walletId && walletId) {
          console.log('🔑 HD wallet keys generated:', data);
          loadWalletData(walletId);
        }
      })
    ];

    return () => {
      subscriptions.forEach(subscriptionId => {
        if (subscriptionId) {
          unsubscribe(subscriptionId);
        }
      });
    };
  }, [walletId]);

  // Load wallet data
  const loadWalletData = async (id: string) => {
    if (!id) return;
    
    try {
      setIsLoading(true);
      
      emit('master_wallet.get_details', {
        wallet_id: id,
        include_performance: true,
        include_allocations: true
      });
      
    } catch (error) {
      console.error('Failed to load wallet data:', error);
    } finally {
      setIsLoading(false);
    }
  };

  // Load all wallets
  const loadWallets = async () => {
    try {
      emit('master_wallet.list_all', {
        include_performance: true
      });
    } catch (error) {
      console.error('Failed to load wallets:', error);
    }
  };

  // Initial load
  useEffect(() => {
    loadWallets();
    if (walletId) {
      loadWalletData(walletId);
    }
  }, [walletId]);

  // Handle refresh
  const handleRefresh = async () => {
    setIsRefreshing(true);
    
    if (walletId) {
      emit('master_wallet.refresh_balances', {
        wallet_id: walletId
      });
    }
    
    setTimeout(() => setIsRefreshing(false), 2000);
  };

  // Handle rebalance
  const handleRebalance = () => {
    if (!walletId) return;
    
    emit('master_wallet.rebalance', {
      wallet_id: walletId,
      force: true
    });
  };

  // Calculate total chain values
  const chainValues = React.useMemo(() => {
    if (!walletData?.balances) return [];
    
    return Object.entries(walletData.balances).map(([chainType, balance]) => ({
      chain: chainType,
      value: balance.usd_value,
      percentage: (balance.usd_value / walletData.total_balance_usd) * 100,
      ...CHAIN_CONFIG[chainType as keyof typeof CHAIN_CONFIG]
    }));
  }, [walletData]);

  // Filter balances by selected chain
  const filteredBalances = React.useMemo(() => {
    if (!walletData?.balances) return [];
    
    if (selectedChain === 'all') {
      return Object.entries(walletData.balances);
    }
    
    return Object.entries(walletData.balances).filter(([chain]) => chain === selectedChain);
  }, [walletData, selectedChain]);

  if (isLoading && !walletData) {
    return (
      <div className={`bg-white rounded-lg shadow-sm border border-gray-200 p-6 ${className}`}>
        <div className="flex items-center justify-center h-64">
          <div className="flex items-center space-x-3">
            <RefreshCw className="w-6 h-6 text-gray-400 animate-spin" />
            <span className="text-gray-600">Loading wallet data...</span>
          </div>
        </div>
      </div>
    );
  }

  if (!walletData && walletId) {
    return (
      <div className={`bg-white rounded-lg shadow-sm border border-gray-200 p-6 ${className}`}>
        <div className="text-center py-8">
          <Wallet className="w-12 h-12 text-gray-400 mx-auto mb-3" />
          <p className="text-gray-600">Wallet not found</p>
          <button
            onClick={() => onWalletSelect && onWalletSelect('')}
            className="mt-3 px-4 py-2 text-sm font-medium text-blue-600 bg-blue-50 rounded-lg hover:bg-blue-100 transition-colors"
          >
            Select Different Wallet
          </button>
        </div>
      </div>
    );
  }

  if (!walletId) {
    return (
      <div className={`bg-white rounded-lg shadow-sm border border-gray-200 ${className}`}>
        {/* Wallet Selection */}
        <div className="px-6 py-4 border-b border-gray-200">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="p-2 bg-blue-100 rounded-lg">
                <Wallet className="w-5 h-5 text-blue-600" />
              </div>
              <div>
                <h3 className="text-lg font-semibold text-gray-900">Master Wallets</h3>
                <p className="text-sm text-gray-600">
                  Select a wallet or create a new one
                </p>
              </div>
            </div>

            <button
              onClick={onCreateWallet}
              className="flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              <Plus className="w-4 h-4 mr-2" />
              Create Wallet
            </button>
          </div>
        </div>

        {/* Wallets List */}
        <div className="p-6">
          {allWallets.length === 0 ? (
            <div className="text-center py-12">
              <Wallet className="w-16 h-16 text-gray-300 mx-auto mb-4" />
              <h4 className="text-lg font-medium text-gray-900 mb-2">No Wallets Yet</h4>
              <p className="text-gray-600 mb-6">Create your first master wallet to get started</p>
              <button
                onClick={onCreateWallet}
                className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
              >
                Create Master Wallet
              </button>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {allWallets.map((wallet) => (
                <motion.div
                  key={wallet.master_wallet_id}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="p-4 border border-gray-200 rounded-lg hover:border-blue-300 hover:shadow-md transition-all cursor-pointer"
                  onClick={() => onWalletSelect && onWalletSelect(wallet.master_wallet_id)}
                >
                  <div className="flex items-center justify-between mb-3">
                    <h4 className="font-medium text-gray-900">{wallet.name}</h4>
                    <div className={`w-3 h-3 rounded-full ${
                      wallet.status === 'active' ? 'bg-green-400' : 'bg-gray-400'
                    }`} />
                  </div>

                  <div className="space-y-2">
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-gray-600">Total Balance</span>
                      <span className="font-medium">${wallet.total_balance_usd.toLocaleString()}</span>
                    </div>

                    <div className="flex items-center justify-between text-sm">
                      <span className="text-gray-600">Performance</span>
                      <span className={`font-medium ${
                        wallet.performance_metrics.performance_score >= 70 ? 'text-green-600' :
                        wallet.performance_metrics.performance_score >= 50 ? 'text-yellow-600' : 'text-red-600'
                      }`}>
                        {wallet.performance_metrics.performance_score.toFixed(1)}
                      </span>
                    </div>

                    <div className="flex items-center justify-between text-sm">
                      <span className="text-gray-600">Chains</span>
                      <span className="font-medium">{Object.keys(wallet.balances).length}</span>
                    </div>
                  </div>
                </motion.div>
              ))}
            </div>
          )}
        </div>
      </div>
    );
  }

  if (!walletData) {
    return (
      <div className={`bg-white rounded-lg shadow-sm border border-gray-200 ${className}`}>
        <div className="px-6 py-4 text-center text-gray-500">
          Select a wallet to view details
        </div>
      </div>
    );
  }

  return (
    <div className={`bg-white rounded-lg shadow-sm border border-gray-200 ${className}`}>
      {/* Header */}
      <div className="px-6 py-4 border-b border-gray-200">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <div className="p-3 bg-blue-100 rounded-lg">
              <Wallet className="w-6 h-6 text-blue-600" />
            </div>
            
            <div>
              <h2 className="text-xl font-bold text-gray-900">{walletData.name}</h2>
              <p className="text-sm text-gray-600">{walletData.description}</p>
            </div>

            <div className={`px-3 py-1 rounded-full text-sm font-medium ${
              walletData.status === 'active' ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'
            }`}>
              {walletData.status}
            </div>
          </div>

          <div className="flex items-center space-x-3">
            <button
              onClick={() => setShowBalances(!showBalances)}
              className="p-2 text-gray-400 hover:text-gray-600 transition-colors"
              title={showBalances ? 'Hide balances' : 'Show balances'}
            >
              {showBalances ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
            </button>

            <button
              onClick={handleRefresh}
              disabled={isRefreshing}
              className="p-2 text-gray-400 hover:text-gray-600 transition-colors disabled:opacity-50"
            >
              <RefreshCw className={`w-5 h-5 ${isRefreshing ? 'animate-spin' : ''}`} />
            </button>

            <button
              onClick={() => setShowAllocationModal(true)}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              <Settings className="w-4 h-4 mr-2 inline" />
              Manage
            </button>
          </div>
        </div>
      </div>

      {/* Key Metrics */}
      <div className="px-6 py-4 border-b border-gray-200">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
          <div className="text-center">
            <div className="flex items-center justify-center w-12 h-12 bg-green-100 rounded-lg mx-auto mb-2">
              <DollarSign className="w-6 h-6 text-green-600" />
            </div>
            <div className="text-2xl font-bold text-gray-900">
              {showBalances ? `$${walletData.total_balance_usd.toLocaleString()}` : '••••••'}
            </div>
            <p className="text-sm text-gray-600">Total Balance</p>
          </div>

          <div className="text-center">
            <div className="flex items-center justify-center w-12 h-12 bg-blue-100 rounded-lg mx-auto mb-2">
              <PieChart className="w-6 h-6 text-blue-600" />
            </div>
            <div className="text-2xl font-bold text-gray-900">
              {walletData.allocation_efficiency.toFixed(1)}%
            </div>
            <p className="text-sm text-gray-600">Allocated</p>
          </div>

          <div className="text-center">
            <div className="flex items-center justify-center w-12 h-12 bg-purple-100 rounded-lg mx-auto mb-2">
              <BarChart3 className="w-6 h-6 text-purple-600" />
            </div>
            <div className="text-2xl font-bold text-gray-900">
              {walletData.performance_metrics.performance_score.toFixed(1)}
            </div>
            <p className="text-sm text-gray-600">Performance</p>
          </div>

          <div className="text-center">
            <div className="flex items-center justify-center w-12 h-12 bg-yellow-100 rounded-lg mx-auto mb-2">
              <Activity className="w-6 h-6 text-yellow-600" />
            </div>
            <div className="text-2xl font-bold text-gray-900">
              {walletData.performance_metrics.win_rate.toFixed(1)}%
            </div>
            <p className="text-sm text-gray-600">Win Rate</p>
          </div>
        </div>
      </div>

      {/* Chain Distribution */}
      <div className="px-6 py-4 border-b border-gray-200">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-gray-900">Chain Distribution</h3>
          
          <select
            value={selectedChain}
            onChange={(e) => setSelectedChain(e.target.value)}
            className="px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="all">All Chains</option>
            {Object.entries(CHAIN_CONFIG).map(([chain, config]) => (
              <option key={chain} value={chain}>{config.name}</option>
            ))}
          </select>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {chainValues.map((chain) => (
            <div key={chain.chain} className="p-4 border border-gray-200 rounded-lg">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center space-x-3">
                  <div className={`w-8 h-8 ${chain.color} rounded-lg flex items-center justify-center text-white text-sm font-bold`}>
                    {chain.icon}
                  </div>
                  <div>
                    <h4 className="font-medium text-gray-900">{chain.name}</h4>
                    <p className="text-xs text-gray-600">{chain.symbol}</p>
                  </div>
                </div>
                
                <div className="text-right">
                  <p className="font-medium text-gray-900">
                    {showBalances ? `$${chain.value.toLocaleString()}` : '••••'}
                  </p>
                  <p className="text-xs text-gray-600">{chain.percentage.toFixed(1)}%</p>
                </div>
              </div>

              <div className="w-full bg-gray-200 rounded-full h-2">
                <div
                  className={`h-2 rounded-full ${chain.color}`}
                  style={{ width: `${chain.percentage}%` }}
                />
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Recent Activity */}
      <div className="px-6 py-4">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-gray-900">Recent Activity</h3>
          <button
            onClick={handleRebalance}
            className="px-3 py-2 text-sm font-medium text-blue-600 bg-blue-50 rounded-lg hover:bg-blue-100 transition-colors"
          >
            <Zap className="w-4 h-4 mr-1 inline" />
            Rebalance
          </button>
        </div>

        <div className="space-y-3">
          <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
            <div className="flex items-center space-x-3">
              <div className="w-8 h-8 bg-green-100 rounded-lg flex items-center justify-center">
                <CheckCircle className="w-4 h-4 text-green-600" />
              </div>
              <div>
                <p className="text-sm font-medium text-gray-900">Performance metrics updated</p>
                <p className="text-xs text-gray-600">
                  Score: {walletData.performance_metrics.performance_score.toFixed(1)}/100
                </p>
              </div>
            </div>
            <span className="text-xs text-gray-500">2 min ago</span>
          </div>

          <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
            <div className="flex items-center space-x-3">
              <div className="w-8 h-8 bg-blue-100 rounded-lg flex items-center justify-center">
                <Key className="w-4 h-4 text-blue-600" />
              </div>
              <div>
                <p className="text-sm font-medium text-gray-900">HD wallet keys active</p>
                <p className="text-xs text-gray-600">
                  {Object.keys(walletData.balances).length} chains connected
                </p>
              </div>
            </div>
            <span className="text-xs text-gray-500">5 min ago</span>
          </div>

          <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
            <div className="flex items-center space-x-3">
              <div className="w-8 h-8 bg-purple-100 rounded-lg flex items-center justify-center">
                <Target className="w-4 h-4 text-purple-600" />
              </div>
              <div>
                <p className="text-sm font-medium text-gray-900">Last rebalance completed</p>
                <p className="text-xs text-gray-600">
                  {new Date(walletData.last_rebalance).toLocaleTimeString()}
                </p>
              </div>
            </div>
            <span className="text-xs text-gray-500">
              {new Date(walletData.last_rebalance).toLocaleDateString()}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default WalletOverview;