ALTER PUBLICATION supabase_realtime ADD TABLE public.products;
ALTER PUBLICATION supabase_realtime ADD TABLE public.orders;
ALTER PUBLICATION supabase_realtime ADD TABLE public.inventory_logs;
ALTER PUBLICATION supabase_realtime ADD TABLE public.agent_runs;
ALTER PUBLICATION supabase_realtime ADD TABLE public.low_stock_events;
ALTER PUBLICATION supabase_realtime ADD TABLE public.delivery_requests;

ALTER TABLE public.products REPLICA IDENTITY FULL;
ALTER TABLE public.orders REPLICA IDENTITY FULL;
ALTER TABLE public.inventory_logs REPLICA IDENTITY FULL;
ALTER TABLE public.agent_runs REPLICA IDENTITY FULL;
ALTER TABLE public.low_stock_events REPLICA IDENTITY FULL;
ALTER TABLE public.delivery_requests REPLICA IDENTITY FULL;
