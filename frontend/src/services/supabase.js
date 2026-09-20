import { createClient } from '@supabase/supabase-js';

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL || 'https://tbaliltgyaqgffrgmtpq.supabase.co';
const supabasePublishableKey = import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY || 'sb_publishable_lJEexuTcTHWcgmoEA5gNpw_N41M4Slh';

// SECURITY: Public client uses ONLY the publishable key.
// Service role key is NEVER bundled or accessed in client-side code.
export const supabase = createClient(supabaseUrl, supabasePublishableKey, {
  realtime: {
    params: {
      eventsPerSecond: 10,
    },
  },
});

/**
 * Subscribe to realtime PostgreSQL changes across KiranaOS tables.
 * Returns the unsubscribe cleanup function.
 */
export function subscribeToRealtimeChanges(handlers = {}) {
  const {
    onProductChange,
    onOrderChange,
    onAgentRunChange,
    onLowStockChange,
    onDeliveryChange,
    onEventLog
  } = handlers;

  const channel = supabase
    .channel('kiranaos-realtime-sync')
    // 1. Products (Stock mutations, dynamic pricing)
    .on(
      'postgres_changes',
      { event: '*', schema: 'public', table: 'products' },
      (payload) => {
        if (onEventLog) {
          onEventLog({
            table: 'products',
            eventType: payload.eventType,
            timestamp: new Date().toLocaleTimeString(),
            record: payload.new || payload.old
          });
        }
        if (onProductChange) onProductChange(payload);
      }
    )
    // 2. Orders (State transitions, confirmation, pending approval)
    .on(
      'postgres_changes',
      { event: '*', schema: 'public', table: 'orders' },
      (payload) => {
        if (onEventLog) {
          onEventLog({
            table: 'orders',
            eventType: payload.eventType,
            timestamp: new Date().toLocaleTimeString(),
            record: payload.new || payload.old
          });
        }
        if (onOrderChange) onOrderChange(payload);
      }
    )
    // 3. Agent Runs (LangGraph DAG step execution & observability)
    .on(
      'postgres_changes',
      { event: '*', schema: 'public', table: 'agent_runs' },
      (payload) => {
        if (onEventLog) {
          onEventLog({
            table: 'agent_runs',
            eventType: payload.eventType,
            timestamp: new Date().toLocaleTimeString(),
            record: payload.new || payload.old
          });
        }
        if (onAgentRunChange) onAgentRunChange(payload);
      }
    )
    // 4. Low Stock Events (Automated inventory thresholds)
    .on(
      'postgres_changes',
      { event: '*', schema: 'public', table: 'low_stock_events' },
      (payload) => {
        if (onEventLog) {
          onEventLog({
            table: 'low_stock_events',
            eventType: payload.eventType,
            timestamp: new Date().toLocaleTimeString(),
            record: payload.new || payload.old
          });
        }
        if (onLowStockChange) onLowStockChange(payload);
      }
    )
    // 5. Delivery Requests (Dispatch & rider status)
    .on(
      'postgres_changes',
      { event: '*', schema: 'public', table: 'delivery_requests' },
      (payload) => {
        if (onEventLog) {
          onEventLog({
            table: 'delivery_requests',
            eventType: payload.eventType,
            timestamp: new Date().toLocaleTimeString(),
            record: payload.new || payload.old
          });
        }
        if (onDeliveryChange) onDeliveryChange(payload);
      }
    )
    .subscribe((status, err) => {
      if (err) {
        console.error('Supabase Realtime subscription error:', err);
      } else {
        console.log(`[Supabase Realtime] Channel status: ${status}`);
      }
    });

  return () => {
    supabase.removeChannel(channel);
  };
}
