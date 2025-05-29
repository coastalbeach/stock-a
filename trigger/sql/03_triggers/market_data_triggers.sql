-- 文件功能：定义与行情数据相关的触发器，用于生成周频和月频数据。
-- 创建日期：YYYY-MM-DD (请替换为实际创建日期)
-- 创建人：AI Assistant

-- 清理旧触发器 (如果存在)
DROP TRIGGER IF EXISTS trg_after_daily_data_changed ON public."股票历史行情_不复权";
DROP TRIGGER IF EXISTS trg_after_daily_hfq_data_changed ON public."股票历史行情_后复权";

-- 触发器：trg_after_daily_data_changed
-- 在 "股票历史行情_不复权" 表发生 INSERT 或 UPDATE 操作后执行 calculate_and_update_periodic_data 函数。
-- 该触发器用于在日频数据更新时，自动计算并更新周频和月频的历史行情数据。
CREATE TRIGGER trg_after_daily_data_changed
AFTER INSERT OR UPDATE ON public."股票历史行情_不复权"
    FOR EACH ROW EXECUTE FUNCTION public.calculate_and_update_periodic_data();

COMMENT ON TRIGGER trg_after_daily_data_changed ON public."股票历史行情_不复权"
    IS '当日频历史行情数据插入或更新时，触发函数以计算并更新周频和月频历史行情数据。';

-- 触发器：trg_after_daily_hfq_data_changed
-- 在 "股票历史行情_后复权" 表发生 INSERT 或 UPDATE 操作后执行 calculate_and_update_periodic_hfq_data 函数。
-- 该触发器用于在后复权日频数据更新时，自动计算并更新后复权的周频和月频历史行情数据。
CREATE TRIGGER trg_after_daily_hfq_data_changed
AFTER INSERT OR UPDATE ON public."股票历史行情_后复权"
    FOR EACH ROW EXECUTE FUNCTION public.calculate_and_update_periodic_hfq_data();

COMMENT ON TRIGGER trg_after_daily_hfq_data_changed ON public."股票历史行情_后复权"
    IS '当后复权日频历史行情数据插入或更新时，触发函数以计算并更新后复权的周频和月频历史行情数据。';

-- 文件结束 --