-- 文件功能：定义与复权因子和后复权价格计算相关的触发器。
-- 创建日期：YYYY-MM-DD (请替换为实际创建日期)
-- 创建人：AI Assistant

-- 清理旧触发器 (如果存在)
DROP TRIGGER IF EXISTS trg_update_hfq_factor_on_dividend_change ON public."除权除息信息";
DROP TRIGGER IF EXISTS trg_calculate_hfq_price_on_daily_data_change ON public."股票历史行情_不复权";
DROP TRIGGER IF EXISTS trg_calculate_hfq_price_on_factor_change ON public."复权因子表";

-- 触发器：trg_update_hfq_factor_on_dividend_change
-- 在 "除权除息信息" 表发生变动时，触发 update_hfq_factor_on_dividend_change 函数。
-- 用于在除权除息信息更新后，重新计算并更新相关股票的后复权因子。
CREATE TRIGGER trg_update_hfq_factor_on_dividend_change
AFTER INSERT OR UPDATE OR DELETE ON public."除权除息信息"
    FOR EACH ROW EXECUTE FUNCTION public.update_hfq_factor_on_dividend_change();

COMMENT ON TRIGGER trg_update_hfq_factor_on_dividend_change ON public."除权除息信息"
    IS '当除权除息信息表发生变动时，触发函数以更新后复权因子。';

-- 触发器：trg_calculate_hfq_price_on_daily_data_change
-- 在 "股票历史行情_不复权" 表发生 INSERT 或 UPDATE 操作后执行 calculate_and_insert_hfq_price 函数。
-- 用于在不复权日行情数据更新时，计算并插入或更新后复权价格。
CREATE TRIGGER trg_calculate_hfq_price_on_daily_data_change
AFTER INSERT OR UPDATE ON public."股票历史行情_不复权"
    FOR EACH ROW EXECUTE FUNCTION public.calculate_and_insert_hfq_price();

COMMENT ON TRIGGER trg_calculate_hfq_price_on_daily_data_change ON public."股票历史行情_不复权"
    IS '当不复权日行情数据更新时，触发函数以计算并更新后复权价格。';

-- 触发器：trg_calculate_hfq_price_on_factor_change
-- 在 "复权因子表" 表发生 UPDATE 操作后执行 calculate_and_insert_hfq_price 函数。
-- 注意：通常我们只关心复权因子的更新，插入新的复权因子记录时，对应的不复权行情可能还未存在，
-- 或者应该由 "股票历史行情_不复权" 表的触发器来处理首次计算。
-- 但为了覆盖因子更新后重新计算已存在的后复权价格的场景，我们监听 UPDATE。
CREATE TRIGGER trg_calculate_hfq_price_on_factor_change
AFTER UPDATE ON public."复权因子表"
    FOR EACH ROW
    WHEN (OLD."后复权因子" IS DISTINCT FROM NEW."后复权因子") -- 仅当后复权因子实际发生变化时触发
    EXECUTE FUNCTION public.calculate_and_insert_hfq_price();

COMMENT ON TRIGGER trg_calculate_hfq_price_on_factor_change ON public."复权因子表"
    IS '当复权因子表中的后复权因子更新时，触发函数以重新计算并更新对应的后复权行情数据。';

-- 文件结束 --