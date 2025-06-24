/**
 * Agent Chat Interface Component
 * Phase 10: Real-time multi-agent communication with LLM integration
 */

import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  MessageCircle,
  Send,
  Bot,
  Brain,
  TrendingUp,
  Shield,
  Target,
  AlertTriangle,
  CheckCircle,
  Clock,
  Users,
  Settings,
  Mic,
  MicOff,
  Volume2,
  VolumeX,
  MoreVertical,
  Star,
  Flag
} from 'lucide-react';

import { eventTransport, subscribe, unsubscribe, emit } from '../../ag-ui-setup/event-transport';

interface AgentPersonality {
  agent_id: string;
  name: string;
  role: string;
  trading_style: string;
  communication_style: string;
  expertise_areas: string[];
  avatar_color: string;
  status: 'online' | 'busy' | 'offline';
}

interface ConversationMessage {
  message_id: string;
  conversation_id: string;
  sender_id: string;
  recipient_id: string;
  content: string;
  message_type: 'discussion' | 'proposal' | 'decision' | 'question' | 'answer' | 'alert' | 'summary';
  timestamp: string;
  context: Record<string, any>;
  is_read: boolean;
  reactions: Array<{ agent_id: string; reaction: string }>;
}

interface ActiveConversation {
  conversation_id: string;
  topic: string;
  participants: string[];
  created_at: string;
  message_count: number;
  last_activity: string;
  priority: number;
}

interface AgentChatInterfaceProps {
  className?: string;
  defaultConversationId?: string;
}

const AGENT_PERSONALITIES: Record<string, AgentPersonality> = {
  'trend_follower_001': {
    agent_id: 'trend_follower_001',
    name: 'Marcus Momentum',
    role: 'Trend Following Specialist',
    trading_style: 'Aggressive Momentum',
    communication_style: 'Confident & Analytical',
    expertise_areas: ['Trend Analysis', 'Momentum Indicators', 'Breakout Patterns'],
    avatar_color: 'bg-blue-500',
    status: 'online'
  },
  'arbitrage_bot_003': {
    agent_id: 'arbitrage_bot_003',
    name: 'Alex Arbitrage',
    role: 'Arbitrage Specialist',
    trading_style: 'Risk-Neutral Arbitrage',
    communication_style: 'Precise & Mathematical',
    expertise_areas: ['Price Discrepancies', 'Cross-Exchange Analysis', 'Statistical Arbitrage'],
    avatar_color: 'bg-green-500',
    status: 'online'
  },
  'mean_reversion_002': {
    agent_id: 'mean_reversion_002',
    name: 'Sophia Reversion',
    role: 'Mean Reversion Strategist',
    trading_style: 'Conservative Mean Reversion',
    communication_style: 'Thoughtful & Cautious',
    expertise_areas: ['Oversold Conditions', 'Support/Resistance', 'Statistical Mean Reversion'],
    avatar_color: 'bg-purple-500',
    status: 'busy'
  },
  'risk_manager_007': {
    agent_id: 'risk_manager_007',
    name: 'Riley Risk',
    role: 'Portfolio Risk Manager',
    trading_style: 'Defensive Risk Management',
    communication_style: 'Authoritative & Protective',
    expertise_areas: ['Portfolio Risk', 'Volatility Analysis', 'Correlation Monitoring'],
    avatar_color: 'bg-red-500',
    status: 'online'
  }
};

const MESSAGE_TYPE_ICONS = {
  discussion: MessageCircle,
  proposal: Target,
  decision: CheckCircle,
  question: MessageCircle,
  answer: CheckCircle,
  alert: AlertTriangle,
  summary: Brain
};

const MESSAGE_TYPE_COLORS = {
  discussion: 'border-gray-300',
  proposal: 'border-blue-400 bg-blue-50',
  decision: 'border-green-400 bg-green-50',
  question: 'border-yellow-400 bg-yellow-50',
  answer: 'border-green-300 bg-green-50',
  alert: 'border-red-400 bg-red-50',
  summary: 'border-purple-400 bg-purple-50'
};

export const AgentChatInterface: React.FC<AgentChatInterfaceProps> = ({
  className = '',
  defaultConversationId
}) => {
  const [activeConversation, setActiveConversation] = useState<ActiveConversation | null>(null);
  const [conversations, setConversations] = useState<ActiveConversation[]>([]);
  const [messages, setMessages] = useState<ConversationMessage[]>([]);
  const [newMessage, setNewMessage] = useState('');
  const [messageType, setMessageType] = useState<ConversationMessage['message_type']>('discussion');
  const [isTyping, setIsTyping] = useState<Record<string, boolean>>({});
  const [selectedAgents, setSelectedAgents] = useState<string[]>([]);
  const [showCreateConversation, setShowCreateConversation] = useState(false);
  const [conversationTopic, setConversationTopic] = useState('');
  const [audioEnabled, setAudioEnabled] = useState(false);
  const [notifications, setNotifications] = useState(true);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const messageInputRef = useRef<HTMLInputElement>(null);

  // Subscribe to agent communication events
  useEffect(() => {
    const subscriptions = [
      subscribe('conversation.started', (data) => {
        console.log('🗣️ New conversation started:', data);
        loadConversations();
      }),

      subscribe('conversation.message_sent', (data) => {
        if (data.conversation_id === activeConversation?.conversation_id) {
          console.log('💬 New message received:', data);
          loadMessages(data.conversation_id);
        }
      }),

      subscribe('agent.typing', (data) => {
        if (data.conversation_id === activeConversation?.conversation_id) {
          setIsTyping(prev => ({
            ...prev,
            [data.agent_id]: true
          }));
          
          // Clear typing indicator after 3 seconds
          setTimeout(() => {
            setIsTyping(prev => ({
              ...prev,
              [data.agent_id]: false
            }));
          }, 3000);
        }
      }),

      subscribe('llm.analysis_complete', (data) => {
        if (data.conversation_id) {
          loadMessages(data.conversation_id);
        }
      })
    ];

    return () => {
      subscriptions.forEach(subscriptionId => {
        if (typeof subscriptionId === 'string') {
          unsubscribe(subscriptionId);
        }
      });
    };
  }, [activeConversation?.conversation_id]);

  // Load conversations on mount
  useEffect(() => {
    loadConversations();
    if (defaultConversationId) {
      loadConversation(defaultConversationId);
    }
  }, [defaultConversationId]);

  // Auto-scroll to bottom of messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const loadConversations = async () => {
    // Mock conversations data
    const mockConversations: ActiveConversation[] = [
      {
        conversation_id: 'conv_001',
        topic: 'Market Analysis: BTC/USD Trend',
        participants: ['trend_follower_001', 'arbitrage_bot_003', 'risk_manager_007'],
        created_at: '2025-06-14T14:30:00Z',
        message_count: 15,
        last_activity: '2025-06-14T15:45:00Z',
        priority: 8
      },
      {
        conversation_id: 'conv_002',
        topic: 'Portfolio Rebalancing Strategy',
        participants: ['mean_reversion_002', 'risk_manager_007'],
        created_at: '2025-06-14T13:15:00Z',
        message_count: 8,
        last_activity: '2025-06-14T15:30:00Z',
        priority: 6
      },
      {
        conversation_id: 'conv_003',
        topic: 'Risk Assessment: High Volatility Alert',
        participants: ['risk_manager_007', 'trend_follower_001', 'mean_reversion_002', 'arbitrage_bot_003'],
        created_at: '2025-06-14T15:00:00Z',
        message_count: 23,
        last_activity: '2025-06-14T15:50:00Z',
        priority: 9
      }
    ];

    setConversations(mockConversations);
  };

  const loadConversation = async (conversationId: string) => {
    const conversation = conversations.find(c => c.conversation_id === conversationId);
    if (conversation) {
      setActiveConversation(conversation);
      await loadMessages(conversationId);
    }
  };

  const loadMessages = async (conversationId: string) => {
    // Mock messages data
    const mockMessages: ConversationMessage[] = [
      {
        message_id: 'msg_001',
        conversation_id: conversationId,
        sender_id: 'trend_follower_001',
        recipient_id: 'all',
        content: 'I\'m seeing strong bullish momentum on BTC/USD. The 20-day MA just crossed above the 50-day MA, and volume is increasing. RSI is at 65, indicating strong momentum without being overbought yet.',
        message_type: 'discussion',
        timestamp: '2025-06-14T14:30:15Z',
        context: { symbols: ['BTC/USD'], indicators: ['MA', 'RSI', 'Volume'] },
        is_read: true,
        reactions: [{ agent_id: 'arbitrage_bot_003', reaction: '👍' }]
      },
      {
        message_id: 'msg_002',
        conversation_id: conversationId,
        sender_id: 'arbitrage_bot_003',
        recipient_id: 'all',
        content: 'Confirmed. I\'m seeing a 0.15% price discrepancy between Binance and Coinbase. The momentum Marcus mentioned is creating arbitrage opportunities. Current spread suggests continued upward pressure.',
        message_type: 'discussion',
        timestamp: '2025-06-14T14:32:20Z',
        context: { exchanges: ['Binance', 'Coinbase'], spread: 0.15 },
        is_read: true,
        reactions: []
      },
      {
        message_id: 'msg_003',
        conversation_id: conversationId,
        sender_id: 'risk_manager_007',
        recipient_id: 'all',
        content: '⚠️ RISK ALERT: Current portfolio exposure to BTC is at 35%. Recommend limiting additional long positions to maintain risk parameters. Consider position sizing carefully.',
        message_type: 'alert',
        timestamp: '2025-06-14T14:35:10Z',
        context: { current_exposure: 35, max_exposure: 40, risk_level: 'medium' },
        is_read: true,
        reactions: [
          { agent_id: 'trend_follower_001', reaction: '✅' },
          { agent_id: 'arbitrage_bot_003', reaction: '✅' }
        ]
      },
      {
        message_id: 'msg_004',
        conversation_id: conversationId,
        sender_id: 'mean_reversion_002',
        recipient_id: 'all',
        content: 'I agree with the bullish sentiment, but I\'m watching for potential reversion signals around the $45,000 resistance level. Historical data shows profit-taking typically occurs at this level.',
        message_type: 'discussion',
        timestamp: '2025-06-14T14:37:45Z',
        context: { resistance_level: 45000, strategy: 'mean_reversion' },
        is_read: true,
        reactions: []
      },
      {
        message_id: 'msg_005',
        conversation_id: conversationId,
        sender_id: 'trend_follower_001',
        recipient_id: 'all',
        content: '📊 PROPOSAL: Open BTC/USD long position, 2% portfolio allocation, entry at current levels (~$43,200), stop loss at $41,500, take profit at $46,000. Risk/reward ratio: 1:1.65',
        message_type: 'proposal',
        timestamp: '2025-06-14T14:40:30Z',
        context: {
          action: 'long',
          symbol: 'BTC/USD',
          allocation: 2,
          entry: 43200,
          stop_loss: 41500,
          take_profit: 46000,
          risk_reward: 1.65
        },
        is_read: true,
        reactions: [{ agent_id: 'arbitrage_bot_003', reaction: '👍' }]
      }
    ];

    setMessages(mockMessages);
  };

  const sendMessage = async () => {
    if (!newMessage.trim() || !activeConversation) return;

    const message: ConversationMessage = {
      message_id: `msg_${Date.now()}`,
      conversation_id: activeConversation.conversation_id,
      sender_id: 'human_trader',
      recipient_id: 'all',
      content: newMessage,
      message_type: messageType,
      timestamp: new Date().toISOString(),
      context: {},
      is_read: false,
      reactions: []
    };

    // Add message to local state
    setMessages(prev => [...prev, message]);

    // Emit message event
    emit('conversation.send_message', {
      conversation_id: activeConversation.conversation_id,
      sender_id: 'human_trader',
      content: newMessage,
      message_type: messageType,
      context: {}
    });

    // Clear input
    setNewMessage('');
    setMessageType('discussion');

    // Focus back to input
    messageInputRef.current?.focus();
  };

  const startNewConversation = async () => {
    if (!conversationTopic.trim() || selectedAgents.length === 0) return;

    emit('conversation.create', {
      topic: conversationTopic,
      participants: [...selectedAgents, 'human_trader'],
      context: {
        created_by: 'human_trader',
        priority: 5
      }
    });

    // Reset form
    setConversationTopic('');
    setSelectedAgents([]);
    setShowCreateConversation(false);
  };

  const addReaction = (messageId: string, reaction: string) => {
    setMessages(prev =>
      prev.map(msg =>
        msg.message_id === messageId
          ? {
              ...msg,
              reactions: [
                ...msg.reactions.filter(r => r.agent_id !== 'human_trader'),
                { agent_id: 'human_trader', reaction }
              ]
            }
          : msg
      )
    );
  };

  const getAgentAvatar = (agentId: string) => {
    const personality = AGENT_PERSONALITIES[agentId];
    if (!personality) {
      return <div className="w-8 h-8 bg-gray-400 rounded-full flex items-center justify-center text-white text-xs font-bold">?</div>;
    }

    return (
      <div className={`w-8 h-8 ${personality.avatar_color} rounded-full flex items-center justify-center text-white text-xs font-bold relative`}>
        {personality.name.charAt(0)}
        {personality.status === 'online' && (
          <div className="absolute -bottom-1 -right-1 w-3 h-3 bg-green-400 border-2 border-white rounded-full"></div>
        )}
        {personality.status === 'busy' && (
          <div className="absolute -bottom-1 -right-1 w-3 h-3 bg-yellow-400 border-2 border-white rounded-full"></div>
        )}
      </div>
    );
  };

  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);

    if (diffMins < 1) return 'now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffMins < 1440) return `${Math.floor(diffMins / 60)}h ago`;
    return date.toLocaleDateString();
  };

  return (
    <div className={`bg-white rounded-lg shadow-lg border border-gray-200 ${className}`}>
      {/* Header */}
      <div className="px-6 py-4 border-b border-gray-200">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="p-2 bg-blue-100 rounded-lg">
              <MessageCircle className="w-5 h-5 text-blue-600" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-gray-900">Agent Communication</h3>
              <p className="text-sm text-gray-600">
                Real-time multi-agent conversations and decision making
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-2">
            <button
              onClick={() => setAudioEnabled(!audioEnabled)}
              className={`p-2 rounded-lg transition-colors ${
                audioEnabled ? 'bg-green-100 text-green-600' : 'bg-gray-100 text-gray-600'
              }`}
              title={audioEnabled ? 'Disable audio' : 'Enable audio'}
            >
              {audioEnabled ? <Volume2 className="w-4 h-4" /> : <VolumeX className="w-4 h-4" />}
            </button>

            <button
              onClick={() => setNotifications(!notifications)}
              className={`p-2 rounded-lg transition-colors ${
                notifications ? 'bg-blue-100 text-blue-600' : 'bg-gray-100 text-gray-600'
              }`}
              title={notifications ? 'Disable notifications' : 'Enable notifications'}
            >
              {notifications ? <CheckCircle className="w-4 h-4" /> : <Clock className="w-4 h-4" />}
            </button>

            <button
              onClick={() => setShowCreateConversation(true)}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              <Users className="w-4 h-4 mr-2 inline" />
              New Chat
            </button>
          </div>
        </div>
      </div>

      <div className="flex h-96">
        {/* Conversations Sidebar */}
        <div className="w-1/3 border-r border-gray-200 flex flex-col">
          <div className="p-4 border-b border-gray-200">
            <h4 className="font-medium text-gray-900">Active Conversations</h4>
          </div>

          <div className="flex-1 overflow-y-auto">
            {conversations.map((conversation) => (
              <motion.div
                key={conversation.conversation_id}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                className={`p-4 border-b border-gray-100 cursor-pointer hover:bg-gray-50 transition-colors ${
                  activeConversation?.conversation_id === conversation.conversation_id ? 'bg-blue-50 border-blue-200' : ''
                }`}
                onClick={() => loadConversation(conversation.conversation_id)}
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1 min-w-0">
                    <h5 className="font-medium text-gray-900 truncate">{conversation.topic}</h5>
                    <p className="text-sm text-gray-600 mt-1">
                      {conversation.participants.length} participants • {conversation.message_count} messages
                    </p>
                    <p className="text-xs text-gray-500 mt-1">
                      {formatTimestamp(conversation.last_activity)}
                    </p>
                  </div>
                  
                  {conversation.priority >= 8 && (
                    <div className="flex-shrink-0 ml-2">
                      <div className="w-2 h-2 bg-red-400 rounded-full"></div>
                    </div>
                  )}
                </div>

                <div className="flex items-center mt-2 space-x-1">
                  {conversation.participants.slice(0, 3).map((agentId) => (
                    <div key={agentId} className="scale-75">
                      {getAgentAvatar(agentId)}
                    </div>
                  ))}
                  {conversation.participants.length > 3 && (
                    <div className="text-xs text-gray-500 ml-1">
                      +{conversation.participants.length - 3}
                    </div>
                  )}
                </div>
              </motion.div>
            ))}
          </div>
        </div>

        {/* Chat Interface */}
        <div className="flex-1 flex flex-col">
          {activeConversation ? (
            <>
              {/* Chat Header */}
              <div className="p-4 border-b border-gray-200">
                <div className="flex items-center justify-between">
                  <div>
                    <h4 className="font-medium text-gray-900">{activeConversation.topic}</h4>
                    <div className="flex items-center space-x-4 mt-1">
                      <div className="flex items-center space-x-1">
                        {activeConversation.participants.map((agentId) => (
                          <div key={agentId} className="scale-75">
                            {getAgentAvatar(agentId)}
                          </div>
                        ))}
                      </div>
                      <span className="text-sm text-gray-600">
                        {activeConversation.participants.length} participants
                      </span>
                    </div>
                  </div>

                  <button className="p-2 text-gray-400 hover:text-gray-600 transition-colors">
                    <MoreVertical className="w-4 h-4" />
                  </button>
                </div>
              </div>

              {/* Messages */}
              <div className="flex-1 overflow-y-auto p-4 space-y-4">
                <AnimatePresence>
                  {messages.map((message) => {
                    const personality = AGENT_PERSONALITIES[message.sender_id];
                    const MessageTypeIcon = MESSAGE_TYPE_ICONS[message.message_type];
                    
                    return (
                      <motion.div
                        key={message.message_id}
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -20 }}
                        className={`border rounded-lg p-4 ${MESSAGE_TYPE_COLORS[message.message_type]}`}
                      >
                        <div className="flex items-start space-x-3">
                          {getAgentAvatar(message.sender_id)}
                          
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center space-x-2 mb-2">
                              <span className="font-medium text-gray-900">
                                {personality?.name || message.sender_id}
                              </span>
                              <MessageTypeIcon className="w-4 h-4 text-gray-500" />
                              <span className="text-xs text-gray-500">
                                {formatTimestamp(message.timestamp)}
                              </span>
                            </div>
                            
                            <p className="text-gray-800 whitespace-pre-wrap">{message.content}</p>
                            
                            {/* Context Display */}
                            {Object.keys(message.context).length > 0 && (
                              <div className="mt-2 p-2 bg-gray-50 rounded text-xs">
                                {Object.entries(message.context).map(([key, value]) => (
                                  <div key={key} className="flex justify-between">
                                    <span className="text-gray-600">{key}:</span>
                                    <span className="text-gray-800 font-mono">
                                      {typeof value === 'object' ? JSON.stringify(value) : String(value)}
                                    </span>
                                  </div>
                                ))}
                              </div>
                            )}

                            {/* Reactions */}
                            <div className="flex items-center space-x-2 mt-3">
                              <div className="flex space-x-1">
                                {['👍', '👎', '🤔', '⚠️'].map((reaction) => (
                                  <button
                                    key={reaction}
                                    onClick={() => addReaction(message.message_id, reaction)}
                                    className="text-sm px-2 py-1 rounded hover:bg-gray-100 transition-colors"
                                  >
                                    {reaction}
                                  </button>
                                ))}
                              </div>
                              
                              {message.reactions.length > 0 && (
                                <div className="flex space-x-1 ml-2">
                                  {message.reactions.map((reaction, idx) => (
                                    <span
                                      key={idx}
                                      className="text-xs bg-gray-100 px-2 py-1 rounded-full"
                                    >
                                      {reaction.reaction}
                                    </span>
                                  ))}
                                </div>
                              )}
                            </div>
                          </div>
                        </div>
                      </motion.div>
                    );
                  })}
                </AnimatePresence>

                {/* Typing Indicators */}
                {Object.entries(isTyping).map(([agentId, typing]) =>
                  typing ? (
                    <motion.div
                      key={agentId}
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: -10 }}
                      className="flex items-center space-x-2 text-gray-500"
                    >
                      {getAgentAvatar(agentId)}
                      <span className="text-sm">{AGENT_PERSONALITIES[agentId]?.name} is typing...</span>
                      <div className="flex space-x-1">
                        <div className="w-1 h-1 bg-gray-400 rounded-full animate-pulse"></div>
                        <div className="w-1 h-1 bg-gray-400 rounded-full animate-pulse" style={{ animationDelay: '0.2s' }}></div>
                        <div className="w-1 h-1 bg-gray-400 rounded-full animate-pulse" style={{ animationDelay: '0.4s' }}></div>
                      </div>
                    </motion.div>
                  ) : null
                )}

                <div ref={messagesEndRef} />
              </div>

              {/* Message Input */}
              <div className="p-4 border-t border-gray-200">
                <div className="flex items-center space-x-2 mb-2">
                  <select
                    value={messageType}
                    onChange={(e) => setMessageType(e.target.value as ConversationMessage['message_type'])}
                    className="text-sm border border-gray-300 rounded px-2 py-1"
                  >
                    <option value="discussion">Discussion</option>
                    <option value="proposal">Proposal</option>
                    <option value="question">Question</option>
                    <option value="alert">Alert</option>
                  </select>
                </div>

                <div className="flex space-x-3">
                  <input
                    ref={messageInputRef}
                    type="text"
                    value={newMessage}
                    onChange={(e) => setNewMessage(e.target.value)}
                    onKeyPress={(e) => e.key === 'Enter' && sendMessage()}
                    placeholder="Type your message..."
                    className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                  <button
                    onClick={sendMessage}
                    disabled={!newMessage.trim()}
                    className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <Send className="w-4 h-4" />
                  </button>
                </div>
              </div>
            </>
          ) : (
            <div className="flex-1 flex items-center justify-center">
              <div className="text-center">
                <MessageCircle className="w-12 h-12 text-gray-400 mx-auto mb-3" />
                <p className="text-gray-600">Select a conversation to start chatting</p>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Create Conversation Modal */}
      <AnimatePresence>
        {showCreateConversation && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
            onClick={() => setShowCreateConversation(false)}
          >
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              className="bg-white rounded-lg p-6 w-full max-w-md m-4"
              onClick={(e) => e.stopPropagation()}
            >
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Start New Conversation</h3>
              
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Conversation Topic
                  </label>
                  <input
                    type="text"
                    value={conversationTopic}
                    onChange={(e) => setConversationTopic(e.target.value)}
                    placeholder="e.g., Market Analysis for ETH/USD"
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Select Agents
                  </label>
                  <div className="space-y-2">
                    {Object.entries(AGENT_PERSONALITIES).map(([agentId, personality]) => (
                      <label key={agentId} className="flex items-center">
                        <input
                          type="checkbox"
                          checked={selectedAgents.includes(agentId)}
                          onChange={(e) => {
                            if (e.target.checked) {
                              setSelectedAgents([...selectedAgents, agentId]);
                            } else {
                              setSelectedAgents(selectedAgents.filter(id => id !== agentId));
                            }
                          }}
                          className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                        />
                        <div className="ml-3 flex items-center space-x-2">
                          {getAgentAvatar(agentId)}
                          <div>
                            <div className="text-sm font-medium text-gray-900">{personality.name}</div>
                            <div className="text-xs text-gray-600">{personality.role}</div>
                          </div>
                        </div>
                      </label>
                    ))}
                  </div>
                </div>
              </div>

              <div className="flex justify-end space-x-3 mt-6">
                <button
                  onClick={() => setShowCreateConversation(false)}
                  className="px-4 py-2 text-gray-700 bg-gray-200 rounded-lg hover:bg-gray-300 transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={startNewConversation}
                  disabled={!conversationTopic.trim() || selectedAgents.length === 0}
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Start Conversation
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default AgentChatInterface;