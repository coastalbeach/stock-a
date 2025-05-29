-- 文件功能：定义与周频和月频数据计算相关的触发器函数。
-- 创建日期：YYYY-MM-DD (请替换为实际创建日期)
-- 创建人：AI Assistant

-- 清理旧函数 (如果存在)
DROP FUNCTION IF EXISTS public.calculate_and_update_periodic_data() CASCADE;
DROP FUNCTION IF EXISTS public.calculate_and_update_periodic_hfq_data() CASCADE;

-- 函数：calculate_and_update_periodic_data()
-- 当 "股票历史行情_不复权" 表发生 INSERT 或 UPDATE 操作时，
-- 此函数被触发，用于计算并更新 "股票历史行情_周频" 和 "股票历史行情_月频" 表中的数据。
-- 增强版：改进性能、错误处理和日志记录
CREATE OR REPLACE FUNCTION public.calculate_and_update_periodic_data()
RETURNS TRIGGER AS $$
DECLARE
    v_stock_code VARCHAR(10);
    v_date DATE;
    v_year INT;
    v_month INT;
    v_week INT;
    v_week_start DATE;
    v_week_end DATE;
    v_month_start DATE;
    v_month_end DATE;
    v_is_week_end BOOLEAN := FALSE;
    v_is_month_end BOOLEAN := FALSE;
    v_next_trading_day DATE;
    v_prev_week_close NUMERIC;
    v_prev_month_close NUMERIC;
    v_start_time TIMESTAMP;
    v_log_message TEXT;
    v_affected_rows_week INT := 0;
    v_affected_rows_month INT := 0;
    v_week_of_year TEXT;
    v_error_message TEXT;
BEGIN
    v_start_time := clock_timestamp();
    
    v_stock_code := NEW."股票代码";
    v_date := NEW."日期";
    v_year := EXTRACT(YEAR FROM v_date);
    v_month := EXTRACT(MONTH FROM v_date);
    v_week := EXTRACT(WEEK FROM v_date);
    v_week_of_year := v_year || '-W' || LPAD(v_week::TEXT, 2, '0');
    
    v_log_message := format('处理股票 %s 在日期 %s 的周期数据', v_stock_code, v_date);
    RAISE NOTICE '%', v_log_message;
    
    -- 创建日志记录表（如果不存在）
    CREATE TEMP TABLE IF NOT EXISTS periodic_data_calculation_log (
        log_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        stock_code VARCHAR(10),
        trade_date DATE,
        message TEXT,
        status TEXT,
        execution_time NUMERIC
    );

    -- 使用索引优化的查询来确定下一个交易日
    BEGIN
        SELECT MIN("日期") INTO v_next_trading_day
        FROM public."股票历史行情_不复权"
        WHERE "股票代码" = v_stock_code AND "日期" > v_date;

        IF v_next_trading_day IS NULL THEN
            -- 如果没有下一个交易日，说明这是最新的数据点
            v_is_week_end := TRUE;
            v_is_month_end := TRUE;
        ELSE
            -- 检查是否是周末或月末
            IF EXTRACT(WEEK FROM v_next_trading_day) != v_week OR EXTRACT(YEAR FROM v_next_trading_day) != v_year THEN
                v_is_week_end := TRUE;
            END IF;
            IF EXTRACT(MONTH FROM v_next_trading_day) != v_month OR EXTRACT(YEAR FROM v_next_trading_day) != v_year THEN
                v_is_month_end := TRUE;
            END IF;
        END IF;
    EXCEPTION WHEN OTHERS THEN
        v_error_message := format('确定下一交易日时出错: %s', SQLERRM);
        RAISE WARNING '%', v_error_message;
        
        INSERT INTO periodic_data_calculation_log (stock_code, trade_date, message, status, execution_time)
        VALUES (v_stock_code, v_date, v_log_message, 'ERROR: ' || v_error_message, 
                EXTRACT(EPOCH FROM (clock_timestamp() - v_start_time)));
        
        -- 默认假设这是周末和月末，以确保数据被处理
        v_is_week_end := TRUE;
        v_is_month_end := TRUE;
    END;

    -- 处理周频数据
    IF v_is_week_end THEN
        BEGIN
            -- 查找本周的第一个交易日
            SELECT MIN("日期") INTO v_week_start
            FROM public."股票历史行情_不复权"
            WHERE "股票代码" = v_stock_code 
              AND EXTRACT(WEEK FROM "日期") = v_week
              AND EXTRACT(YEAR FROM "日期") = v_year;
              
            IF v_week_start IS NULL THEN
                RAISE WARNING '无法确定股票 % 在 % 周的开始日期', v_stock_code, v_week_of_year;
                v_week_start := v_date; -- 使用当前日期作为备选
            END IF;
            
            v_week_end := v_date;

            -- 查找上一周期的收盘价，用于计算涨跌幅
            SELECT "收盘" INTO v_prev_week_close
            FROM public."股票历史行情_周频"
            WHERE "股票代码" = v_stock_code AND "周期结束日期" = (
                SELECT MAX("周期结束日期") 
                FROM public."股票历史行情_周频" 
                WHERE "股票代码" = v_stock_code AND "周期结束日期" < v_week_start
            );

            -- 使用事务处理插入/更新操作
            INSERT INTO public."股票历史行情_周频" (
                "股票代码", "周期开始日期", "周期结束日期", "开盘", "收盘", "最高", "最低",
                "成交量", "成交额", "涨跌幅", "涨跌额", "交易日数", "更新时间"
            )
            SELECT 
                v_stock_code, v_week_start, v_week_end,
                (SELECT "开盘" FROM public."股票历史行情_不复权" WHERE "股票代码" = v_stock_code AND "日期" = v_week_start),
                NEW."收盘", 
                COALESCE(MAX("最高"), NEW."最高"), 
                COALESCE(MIN("最低"), NEW."最低"), 
                SUM("成交量"), 
                SUM("成交额"),
                CASE WHEN v_prev_week_close IS NOT NULL AND v_prev_week_close <> 0 
                     THEN (NEW."收盘" / v_prev_week_close - 1) * 100 
                     ELSE NULL 
                END,
                CASE WHEN v_prev_week_close IS NOT NULL 
                     THEN NEW."收盘" - v_prev_week_close 
                     ELSE NULL 
                END,
                COUNT(*),
                CURRENT_TIMESTAMP
            FROM public."股票历史行情_不复权"
            WHERE "股票代码" = v_stock_code AND "日期" BETWEEN v_week_start AND v_week_end
            GROUP BY "股票代码"
            ON CONFLICT ("股票代码", "周期结束日期") DO UPDATE SET
                "周期开始日期" = EXCLUDED."周期开始日期", 
                "开盘" = EXCLUDED."开盘", 
                "收盘" = EXCLUDED."收盘",
                "最高" = EXCLUDED."最高", 
                "最低" = EXCLUDED."最低", 
                "成交量" = EXCLUDED."成交量",
                "成交额" = EXCLUDED."成交额", 
                "涨跌幅" = EXCLUDED."涨跌幅", 
                "涨跌额" = EXCLUDED."涨跌额",
                "交易日数" = EXCLUDED."交易日数", 
                "更新时间" = CURRENT_TIMESTAMP;
                
            GET DIAGNOSTICS v_affected_rows_week = ROW_COUNT;
            
            -- 记录成功日志
            INSERT INTO periodic_data_calculation_log (stock_code, trade_date, message, status, execution_time)
            VALUES (v_stock_code, v_date, 
                    format('更新周频数据: %s, 周期: %s 至 %s', v_stock_code, v_week_start, v_week_end),
                    format('SUCCESS: 影响行数 %s', v_affected_rows_week),
                    EXTRACT(EPOCH FROM (clock_timestamp() - v_start_time)));
                    
        EXCEPTION WHEN OTHERS THEN
            v_error_message := format('处理周频数据时出错: %s', SQLERRM);
            RAISE WARNING '%', v_error_message;
            
            INSERT INTO periodic_data_calculation_log (stock_code, trade_date, message, status, execution_time)
            VALUES (v_stock_code, v_date, 
                    format('更新周频数据: %s, 周期: %s', v_stock_code, v_week_of_year),
                    'ERROR: ' || v_error_message,
                    EXTRACT(EPOCH FROM (clock_timestamp() - v_start_time)));
        END;
    END IF;

    -- 处理月频数据
    IF v_is_month_end THEN
        BEGIN
            -- 查找本月的第一个交易日
            SELECT MIN("日期") INTO v_month_start
            FROM public."股票历史行情_不复权"
            WHERE "股票代码" = v_stock_code 
              AND EXTRACT(MONTH FROM "日期") = v_month
              AND EXTRACT(YEAR FROM "日期") = v_year;
              
            IF v_month_start IS NULL THEN
                RAISE WARNING '无法确定股票 % 在 %年%月 的开始日期', v_stock_code, v_year, v_month;
                v_month_start := v_date; -- 使用当前日期作为备选
            END IF;
            
            v_month_end := v_date;

            -- 查找上一月的收盘价，用于计算涨跌幅
            SELECT "收盘" INTO v_prev_month_close
            FROM public."股票历史行情_月频"
            WHERE "股票代码" = v_stock_code AND "周期结束日期" = (
                SELECT MAX("周期结束日期") 
                FROM public."股票历史行情_月频" 
                WHERE "股票代码" = v_stock_code AND "周期结束日期" < v_month_start
            );

            -- 使用事务处理插入/更新操作
            INSERT INTO public."股票历史行情_月频" (
                "股票代码", "周期开始日期", "周期结束日期", "开盘", "收盘", "最高", "最低",
                "成交量", "成交额", "涨跌幅", "涨跌额", "交易日数", "更新时间"
            )
            SELECT 
                v_stock_code, v_month_start, v_month_end,
                (SELECT "开盘" FROM public."股票历史行情_不复权" WHERE "股票代码" = v_stock_code AND "日期" = v_month_start),
                NEW."收盘", 
                COALESCE(MAX("最高"), NEW."最高"), 
                COALESCE(MIN("最低"), NEW."最低"), 
                SUM("成交量"), 
                SUM("成交额"),
                CASE WHEN v_prev_month_close IS NOT NULL AND v_prev_month_close <> 0 
                     THEN (NEW."收盘" / v_prev_month_close - 1) * 100 
                     ELSE NULL 
                END,
                CASE WHEN v_prev_month_close IS NOT NULL 
                     THEN NEW."收盘" - v_prev_month_close 
                     ELSE NULL 
                END,
                COUNT(*),
                CURRENT_TIMESTAMP
            FROM public."股票历史行情_不复权"
            WHERE "股票代码" = v_stock_code AND "日期" BETWEEN v_month_start AND v_month_end
            GROUP BY "股票代码"
            ON CONFLICT ("股票代码", "周期结束日期") DO UPDATE SET
                "周期开始日期" = EXCLUDED."周期开始日期", 
                "开盘" = EXCLUDED."开盘", 
                "收盘" = EXCLUDED."收盘",
                "最高" = EXCLUDED."最高", 
                "最低" = EXCLUDED."最低", 
                "成交量" = EXCLUDED."成交量",
                "成交额" = EXCLUDED."成交额", 
                "涨跌幅" = EXCLUDED."涨跌幅", 
                "涨跌额" = EXCLUDED."涨跌额",
                "交易日数" = EXCLUDED."交易日数", 
                "更新时间" = CURRENT_TIMESTAMP;
                
            GET DIAGNOSTICS v_affected_rows_month = ROW_COUNT;
            
            -- 记录成功日志
            INSERT INTO periodic_data_calculation_log (stock_code, trade_date, message, status, execution_time)
            VALUES (v_stock_code, v_date, 
                    format('更新月频数据: %s, 周期: %s 至 %s', v_stock_code, v_month_start, v_month_end),
                    format('SUCCESS: 影响行数 %s', v_affected_rows_month),
                    EXTRACT(EPOCH FROM (clock_timestamp() - v_start_time)));
                    
        EXCEPTION WHEN OTHERS THEN
            v_error_message := format('处理月频数据时出错: %s', SQLERRM);
            RAISE WARNING '%', v_error_message;
            
            INSERT INTO periodic_data_calculation_log (stock_code, trade_date, message, status, execution_time)
            VALUES (v_stock_code, v_date, 
                    format('更新月频数据: %s, %s年%s月', v_stock_code, v_year, v_month),
                    'ERROR: ' || v_error_message,
                    EXTRACT(EPOCH FROM (clock_timestamp() - v_start_time)));
        END;
    END IF;

    -- 性能日志
    IF EXTRACT(EPOCH FROM (clock_timestamp() - v_start_time)) > 1.0 THEN
        RAISE NOTICE '周期数据计算耗时较长：股票 %，日期 %，耗时 % 秒', 
                     v_stock_code, v_date, EXTRACT(EPOCH FROM (clock_timestamp() - v_start_time));
    END IF;

    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION public.calculate_and_update_periodic_data()
    IS '当日频历史行情数据更新时，计算并更新周频和月频历史行情数据。';

-- 函数：calculate_and_update_periodic_hfq_data()
-- 当 "股票历史行情_后复权" 表发生 INSERT 或 UPDATE 操作时，
-- 此函数被触发，用于计算并更新 "股票历史行情_周频_后复权" 和 "股票历史行情_月频_后复权" 表中的数据。
-- 增强版：改进性能、错误处理和日志记录
CREATE OR REPLACE FUNCTION public.calculate_and_update_periodic_hfq_data()
RETURNS TRIGGER AS $$
DECLARE
    v_stock_code VARCHAR(10);
    v_date DATE;
    v_year INT;
    v_month INT;
    v_week INT;
    v_week_start DATE;
    v_week_end DATE;
    v_month_start DATE;
    v_month_end DATE;
    v_is_week_end BOOLEAN := FALSE;
    v_is_month_end BOOLEAN := FALSE;
    v_next_trading_day DATE;
    v_prev_week_close NUMERIC;
    v_prev_month_close NUMERIC;
    v_start_time TIMESTAMP;
    v_log_message TEXT;
    v_affected_rows_week INT := 0;
    v_affected_rows_month INT := 0;
    v_week_of_year TEXT;
    v_error_message TEXT;
BEGIN
    v_start_time := clock_timestamp();
    
    v_stock_code := NEW."股票代码";
    v_date := NEW."日期";
    v_year := EXTRACT(YEAR FROM v_date);
    v_month := EXTRACT(MONTH FROM v_date);
    v_week := EXTRACT(WEEK FROM v_date);
    v_week_of_year := v_year || '-W' || LPAD(v_week::TEXT, 2, '0');
    
    v_log_message := format('处理股票 %s 在日期 %s 的后复权周期数据', v_stock_code, v_date);
    RAISE NOTICE '%', v_log_message;
    
    -- 创建日志记录表（如果不存在）
    CREATE TEMP TABLE IF NOT EXISTS periodic_hfq_data_calculation_log (
        log_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        stock_code VARCHAR(10),
        trade_date DATE,
        message TEXT,
        status TEXT,
        execution_time NUMERIC
    );

    -- 使用索引优化的查询来确定下一个交易日
    BEGIN
        SELECT MIN("日期") INTO v_next_trading_day
        FROM public."股票历史行情_后复权"
        WHERE "股票代码" = v_stock_code AND "日期" > v_date;

        IF v_next_trading_day IS NULL THEN
            -- 如果没有下一个交易日，说明这是最新的数据点
            v_is_week_end := TRUE;
            v_is_month_end := TRUE;
        ELSE
            -- 检查是否是周末或月末
            IF EXTRACT(WEEK FROM v_next_trading_day) != v_week OR EXTRACT(YEAR FROM v_next_trading_day) != v_year THEN
                v_is_week_end := TRUE;
            END IF;
            IF EXTRACT(MONTH FROM v_next_trading_day) != v_month OR EXTRACT(YEAR FROM v_next_trading_day) != v_year THEN
                v_is_month_end := TRUE;
            END IF;
        END IF;
    EXCEPTION WHEN OTHERS THEN
        v_error_message := format('确定下一交易日时出错: %s', SQLERRM);
        RAISE WARNING '%', v_error_message;
        
        INSERT INTO periodic_hfq_data_calculation_log (stock_code, trade_date, message, status, execution_time)
        VALUES (v_stock_code, v_date, v_log_message, 'ERROR: ' || v_error_message, 
                EXTRACT(EPOCH FROM (clock_timestamp() - v_start_time)));
        
        -- 默认假设这是周末和月末，以确保数据被处理
        v_is_week_end := TRUE;
        v_is_month_end := TRUE;
    END;

    -- 处理周频数据
    IF v_is_week_end THEN
        BEGIN
            -- 查找本周的第一个交易日
            SELECT MIN("日期") INTO v_week_start
            FROM public."股票历史行情_后复权"
            WHERE "股票代码" = v_stock_code 
              AND EXTRACT(WEEK FROM "日期") = v_week
              AND EXTRACT(YEAR FROM "日期") = v_year;
              
            IF v_week_start IS NULL THEN
                RAISE WARNING '无法确定股票 % 在 % 周的开始日期（后复权）', v_stock_code, v_week_of_year;
                v_week_start := v_date; -- 使用当前日期作为备选
            END IF;
            
            v_week_end := v_date;

            -- 查找上一周期的收盘价，用于计算涨跌幅
            SELECT "收盘" INTO v_prev_week_close
            FROM public."股票历史行情_周频_后复权"
            WHERE "股票代码" = v_stock_code AND "周期结束日期" = (
                SELECT MAX("周期结束日期") 
                FROM public."股票历史行情_周频_后复权" 
                WHERE "股票代码" = v_stock_code AND "周期结束日期" < v_week_start
            );

            -- 使用事务处理插入/更新操作
            INSERT INTO public."股票历史行情_周频_后复权" (
                "股票代码", "周期开始日期", "周期结束日期", "开盘", "收盘", "最高", "最低",
                "成交量", "成交额", "涨跌幅", "涨跌额", "交易日数", "更新时间"
            )
            SELECT 
                v_stock_code, v_week_start, v_week_end,
                (SELECT "开盘" FROM public."股票历史行情_后复权" WHERE "股票代码" = v_stock_code AND "日期" = v_week_start),
                NEW."收盘", 
                COALESCE(MAX("最高"), NEW."最高"), 
                COALESCE(MIN("最低"), NEW."最低"), 
                SUM("成交量"), 
                SUM("成交额"),
                CASE WHEN v_prev_week_close IS NOT NULL AND v_prev_week_close <> 0 
                     THEN (NEW."收盘" / v_prev_week_close - 1) * 100 
                     ELSE NULL 
                END,
                CASE WHEN v_prev_week_close IS NOT NULL 
                     THEN NEW."收盘" - v_prev_week_close 
                     ELSE NULL 
                END,
                COUNT(*),
                CURRENT_TIMESTAMP
            FROM public."股票历史行情_后复权"
            WHERE "股票代码" = v_stock_code AND "日期" BETWEEN v_week_start AND v_week_end
            GROUP BY "股票代码"
            ON CONFLICT ("股票代码", "周期结束日期") DO UPDATE SET
                "周期开始日期" = EXCLUDED."周期开始日期", 
                "开盘" = EXCLUDED."开盘", 
                "收盘" = EXCLUDED."收盘",
                "最高" = EXCLUDED."最高", 
                "最低" = EXCLUDED."最低", 
                "成交量" = EXCLUDED."成交量",
                "成交额" = EXCLUDED."成交额", 
                "涨跌幅" = EXCLUDED."涨跌幅", 
                "涨跌额" = EXCLUDED."涨跌额",
                "交易日数" = EXCLUDED."交易日数", 
                "更新时间" = CURRENT_TIMESTAMP;
                
            GET DIAGNOSTICS v_affected_rows_week = ROW_COUNT;
            
            -- 记录成功日志
            INSERT INTO periodic_hfq_data_calculation_log (stock_code, trade_date, message, status, execution_time)
            VALUES (v_stock_code, v_date, 
                    format('更新后复权周频数据: %s, 周期: %s 至 %s', v_stock_code, v_week_start, v_week_end),
                    format('SUCCESS: 影响行数 %s', v_affected_rows_week),
                    EXTRACT(EPOCH FROM (clock_timestamp() - v_start_time)));
                    
        EXCEPTION WHEN OTHERS THEN
            v_error_message := format('处理后复权周频数据时出错: %s', SQLERRM);
            RAISE WARNING '%', v_error_message;
            
            INSERT INTO periodic_hfq_data_calculation_log (stock_code, trade_date, message, status, execution_time)
            VALUES (v_stock_code, v_date, 
                    format('更新后复权周频数据: %s, 周期: %s', v_stock_code, v_week_of_year),
                    'ERROR: ' || v_error_message,
                    EXTRACT(EPOCH FROM (clock_timestamp() - v_start_time)));
        END;
    END IF;

    -- 处理月频数据
    IF v_is_month_end THEN
        BEGIN
            -- 查找本月的第一个交易日
            SELECT MIN("日期") INTO v_month_start
            FROM public."股票历史行情_后复权"
            WHERE "股票代码" = v_stock_code 
              AND EXTRACT(MONTH FROM "日期") = v_month
              AND EXTRACT(YEAR FROM "日期") = v_year;
              
            IF v_month_start IS NULL THEN
                RAISE WARNING '无法确定股票 % 在 %年%月 的开始日期（后复权）', v_stock_code, v_year, v_month;
                v_month_start := v_date; -- 使用当前日期作为备选
            END IF;
            
            v_month_end := v_date;

            -- 查找上一月的收盘价，用于计算涨跌幅
            SELECT "收盘" INTO v_prev_month_close
            FROM public."股票历史行情_月频_后复权"
            WHERE "股票代码" = v_stock_code AND "周期结束日期" = (
                SELECT MAX("周期结束日期") 
                FROM public."股票历史行情_月频_后复权" 
                WHERE "股票代码" = v_stock_code AND "周期结束日期" < v_month_start
            );

            -- 使用事务处理插入/更新操作
            INSERT INTO public."股票历史行情_月频_后复权" (
                "股票代码", "周期开始日期", "周期结束日期", "开盘", "收盘", "最高", "最低",
                "成交量", "成交额", "涨跌幅", "涨跌额", "交易日数", "更新时间"
            )
            SELECT 
                v_stock_code, v_month_start, v_month_end,
                (SELECT "开盘" FROM public."股票历史行情_后复权" WHERE "股票代码" = v_stock_code AND "日期" = v_month_start),
                NEW."收盘", 
                COALESCE(MAX("最高"), NEW."最高"), 
                COALESCE(MIN("最低"), NEW."最低"), 
                SUM("成交量"), 
                SUM("成交额"),
                CASE WHEN v_prev_month_close IS NOT NULL AND v_prev_month_close <> 0 
                     THEN (NEW."收盘" / v_prev_month_close - 1) * 100 
                     ELSE NULL 
                END,
                CASE WHEN v_prev_month_close IS NOT NULL 
                     THEN NEW."收盘" - v_prev_month_close 
                     ELSE NULL 
                END,
                COUNT(*),
                CURRENT_TIMESTAMP
            FROM public."股票历史行情_后复权"
            WHERE "股票代码" = v_stock_code AND "日期" BETWEEN v_month_start AND v_month_end
            GROUP BY "股票代码"
            ON CONFLICT ("股票代码", "周期结束日期") DO UPDATE SET
                "周期开始日期" = EXCLUDED."周期开始日期", 
                "开盘" = EXCLUDED."开盘", 
                "收盘" = EXCLUDED."收盘",
                "最高" = EXCLUDED."最高", 
                "最低" = EXCLUDED."最低", 
                "成交量" = EXCLUDED."成交量",
                "成交额" = EXCLUDED."成交额", 
                "涨跌幅" = EXCLUDED."涨跌幅", 
                "涨跌额" = EXCLUDED."涨跌额",
                "交易日数" = EXCLUDED."交易日数", 
                "更新时间" = CURRENT_TIMESTAMP;
                
            GET DIAGNOSTICS v_affected_rows_month = ROW_COUNT;
            
            -- 记录成功日志
            INSERT INTO periodic_hfq_data_calculation_log (stock_code, trade_date, message, status, execution_time)
            VALUES (v_stock_code, v_date, 
                    format('更新后复权月频数据: %s, 周期: %s 至 %s', v_stock_code, v_month_start, v_month_end),
                    format('SUCCESS: 影响行数 %s', v_affected_rows_month),
                    EXTRACT(EPOCH FROM (clock_timestamp() - v_start_time)));
                    
        EXCEPTION WHEN OTHERS THEN
            v_error_message := format('处理后复权月频数据时出错: %s', SQLERRM);
            RAISE WARNING '%', v_error_message;
            
            INSERT INTO periodic_hfq_data_calculation_log (stock_code, trade_date, message, status, execution_time)
            VALUES (v_stock_code, v_date, 
                    format('更新后复权月频数据: %s, %s年%s月', v_stock_code, v_year, v_month),
                    'ERROR: ' || v_error_message,
                    EXTRACT(EPOCH FROM (clock_timestamp() - v_start_time)));
        END;
    END IF;

    -- 性能日志
    IF EXTRACT(EPOCH FROM (clock_timestamp() - v_start_time)) > 1.0 THEN
        RAISE NOTICE '后复权周期数据计算耗时较长：股票 %，日期 %，耗时 % 秒', 
                     v_stock_code, v_date, EXTRACT(EPOCH FROM (clock_timestamp() - v_start_time));
    END IF;

    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION public.calculate_and_update_periodic_hfq_data()
    IS '当后复权日频历史行情数据更新时，计算并更新后复权的周频和月频历史行情数据。';

-- 文件结束 --