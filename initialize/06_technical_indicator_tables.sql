-- 技术指标相关表：股票技术指标、行业技术指标、指数技术指标

-- Table: public.股票技术指标

-- DROP TABLE IF EXISTS public."股票技术指标";

CREATE TABLE IF NOT EXISTS public."股票技术指标"
(
    "股票代码" character varying(10) COLLATE pg_catalog."default" NOT NULL,
    "日期" date NOT NULL,
    "SMA5" double precision,
    "SMA10" double precision,
    "SMA20" double precision,
    "SMA60" double precision,
    "EMA12" double precision,
    "EMA26" double precision,
    "DIF" double precision,
    "DEA" double precision,
    "MACD_hist" double precision,
    "RSI6" double precision,
    "RSI12" double precision,
    "RSI24" double precision,
    "BBANDS_UPPER" double precision,
    "BBANDS_MIDDLE" double precision,
    "BBANDS_LOWER" double precision,
    "KDJ_K" double precision,
    "KDJ_D" double precision,
    "KDJ_J" double precision,
    "VOL_MA5" double precision,
    "VOL_MA10" double precision,
    "WR14" double precision,
    "CCI14" double precision,
    "PDI14" double precision,
    "MDI14" double precision,
    "ADX14" double precision,
    "ROC6" double precision,
    "ROC12" double precision,
    "BIAS6" double precision,
    "BIAS12" double precision,
    "BIAS24" double precision,
    "OBV" double precision,
    "OBV_MA5" double precision,
    "OBV_MA10" double precision,
    CONSTRAINT "股票技术指标_pkey" PRIMARY KEY ("股票代码", "日期"),
    CONSTRAINT "股票技术指标_fkey" FOREIGN KEY ("股票代码", "日期")
        REFERENCES public."股票历史行情_后复权" ("股票代码", "日期") MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE CASCADE,
    CONSTRAINT "股票技术指标_股票代码_日期_fkey" FOREIGN KEY ("股票代码", "日期")
        REFERENCES public."股票历史行情_后复权_0" ("股票代码", "日期") MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE CASCADE,
    CONSTRAINT "股票技术指标_股票代码_日期_fkey1" FOREIGN KEY ("股票代码", "日期")
        REFERENCES public."股票历史行情_后复权_1" ("股票代码", "日期") MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE CASCADE,
    CONSTRAINT "股票技术指标_股票代码_日期_fkey10" FOREIGN KEY ("股票代码", "日期")
        REFERENCES public."股票历史行情_后复权_10" ("股票代码", "日期") MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE CASCADE,
    CONSTRAINT "股票技术指标_股票代码_日期_fkey11" FOREIGN KEY ("股票代码", "日期")
        REFERENCES public."股票历史行情_后复权_11" ("股票代码", "日期") MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE CASCADE,
    CONSTRAINT "股票技术指标_股票代码_日期_fkey12" FOREIGN KEY ("股票代码", "日期")
        REFERENCES public."股票历史行情_后复权_12" ("股票代码", "日期") MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE CASCADE,
    CONSTRAINT "股票技术指标_股票代码_日期_fkey13" FOREIGN KEY ("股票代码", "日期")
        REFERENCES public."股票历史行情_后复权_13" ("股票代码", "日期") MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE CASCADE,
    CONSTRAINT "股票技术指标_股票代码_日期_fkey14" FOREIGN KEY ("股票代码", "日期")
        REFERENCES public."股票历史行情_后复权_14" ("股票代码", "日期") MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE CASCADE,
    CONSTRAINT "股票技术指标_股票代码_日期_fkey15" FOREIGN KEY ("股票代码", "日期")
        REFERENCES public."股票历史行情_后复权_15" ("股票代码", "日期") MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE CASCADE,
    CONSTRAINT "股票技术指标_股票代码_日期_fkey2" FOREIGN KEY ("股票代码", "日期")
        REFERENCES public."股票历史行情_后复权_2" ("股票代码", "日期") MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE CASCADE,
    CONSTRAINT "股票技术指标_股票代码_日期_fkey3" FOREIGN KEY ("股票代码", "日期")
        REFERENCES public."股票历史行情_后复权_3" ("股票代码", "日期") MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE CASCADE,
    CONSTRAINT "股票技术指标_股票代码_日期_fkey4" FOREIGN KEY ("股票代码", "日期")
        REFERENCES public."股票历史行情_后复权_4" ("股票代码", "日期") MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE CASCADE,
    CONSTRAINT "股票技术指标_股票代码_日期_fkey5" FOREIGN KEY ("股票代码", "日期")
        REFERENCES public."股票历史行情_后复权_5" ("股票代码", "日期") MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE CASCADE,
    CONSTRAINT "股票技术指标_股票代码_日期_fkey6" FOREIGN KEY ("股票代码", "日期")
        REFERENCES public."股票历史行情_后复权_6" ("股票代码", "日期") MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE CASCADE,
    CONSTRAINT "股票技术指标_股票代码_日期_fkey7" FOREIGN KEY ("股票代码", "日期")
        REFERENCES public."股票历史行情_后复权_7" ("股票代码", "日期") MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE CASCADE,
    CONSTRAINT "股票技术指标_股票代码_日期_fkey8" FOREIGN KEY ("股票代码", "日期")
        REFERENCES public."股票历史行情_后复权_8" ("股票代码", "日期") MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE CASCADE,
    CONSTRAINT "股票技术指标_股票代码_日期_fkey9" FOREIGN KEY ("股票代码", "日期")
        REFERENCES public."股票历史行情_后复权_9" ("股票代码", "日期") MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE CASCADE
) PARTITION BY HASH ("股票代码");

ALTER TABLE IF EXISTS public."股票技术指标"
    OWNER to postgres;
-- Index: idx_股票技术指标_日期

-- DROP INDEX IF EXISTS public."idx_股票技术指标_日期";

CREATE INDEX IF NOT EXISTS "idx_股票技术指标_日期"
    ON public."股票技术指标" USING btree
    ("日期" ASC NULLS LAST)
;

-- Partitions SQL

CREATE TABLE public."股票技术指标_p0" PARTITION OF public."股票技术指标"
    FOR VALUES WITH (modulus 16, remainder 0)
TABLESPACE pg_default;

ALTER TABLE IF EXISTS public."股票技术指标_p0"
    OWNER to postgres;
CREATE TABLE public."股票技术指标_p1" PARTITION OF public."股票技术指标"
    FOR VALUES WITH (modulus 16, remainder 1)
TABLESPACE pg_default;

ALTER TABLE IF EXISTS public."股票技术指标_p1"
    OWNER to postgres;
CREATE TABLE public."股票技术指标_p2" PARTITION OF public."股票技术指标"
    FOR VALUES WITH (modulus 16, remainder 2)
TABLESPACE pg_default;

ALTER TABLE IF EXISTS public."股票技术指标_p2"
    OWNER to postgres;
CREATE TABLE public."股票技术指标_p3" PARTITION OF public."股票技术指标"
    FOR VALUES WITH (modulus 16, remainder 3)
TABLESPACE pg_default;

ALTER TABLE IF EXISTS public."股票技术指标_p3"
    OWNER to postgres;
CREATE TABLE public."股票技术指标_p4" PARTITION OF public."股票技术指标"
    FOR VALUES WITH (modulus 16, remainder 4)
TABLESPACE pg_default;

ALTER TABLE IF EXISTS public."股票技术指标_p4"
    OWNER to postgres;
CREATE TABLE public."股票技术指标_p5" PARTITION OF public."股票技术指标"
    FOR VALUES WITH (modulus 16, remainder 5)
TABLESPACE pg_default;

ALTER TABLE IF EXISTS public."股票技术指标_p5"
    OWNER to postgres;
CREATE TABLE public."股票技术指标_p6" PARTITION OF public."股票技术指标"
    FOR VALUES WITH (modulus 16, remainder 6)
TABLESPACE pg_default;

ALTER TABLE IF EXISTS public."股票技术指标_p6"
    OWNER to postgres;
CREATE TABLE public."股票技术指标_p7" PARTITION OF public."股票技术指标"
    FOR VALUES WITH (modulus 16, remainder 7)
TABLESPACE pg_default;

ALTER TABLE IF EXISTS public."股票技术指标_p7"
    OWNER to postgres;
CREATE TABLE public."股票技术指标_p8" PARTITION OF public."股票技术指标"
    FOR VALUES WITH (modulus 16, remainder 8)
TABLESPACE pg_default;

ALTER TABLE IF EXISTS public."股票技术指标_p8"
    OWNER to postgres;
CREATE TABLE public."股票技术指标_p9" PARTITION OF public."股票技术指标"
    FOR VALUES WITH (modulus 16, remainder 9)
TABLESPACE pg_default;

ALTER TABLE IF EXISTS public."股票技术指标_p9"
    OWNER to postgres;
CREATE TABLE public."股票技术指标_p10" PARTITION OF public."股票技术指标"
    FOR VALUES WITH (modulus 16, remainder 10)
TABLESPACE pg_default;

ALTER TABLE IF EXISTS public."股票技术指标_p10"
    OWNER to postgres;
CREATE TABLE public."股票技术指标_p11" PARTITION OF public."股票技术指标"
    FOR VALUES WITH (modulus 16, remainder 11)
TABLESPACE pg_default;

ALTER TABLE IF EXISTS public."股票技术指标_p11"
    OWNER to postgres;
CREATE TABLE public."股票技术指标_p12" PARTITION OF public."股票技术指标"
    FOR VALUES WITH (modulus 16, remainder 12)
TABLESPACE pg_default;

ALTER TABLE IF EXISTS public."股票技术指标_p12"
    OWNER to postgres;
CREATE TABLE public."股票技术指标_p13" PARTITION OF public."股票技术指标"
    FOR VALUES WITH (modulus 16, remainder 13)
TABLESPACE pg_default;

ALTER TABLE IF EXISTS public."股票技术指标_p13"
    OWNER to postgres;
CREATE TABLE public."股票技术指标_p14" PARTITION OF public."股票技术指标"
    FOR VALUES WITH (modulus 16, remainder 14)
TABLESPACE pg_default;

ALTER TABLE IF EXISTS public."股票技术指标_p14"
    OWNER to postgres;
CREATE TABLE public."股票技术指标_p15" PARTITION OF public."股票技术指标"
    FOR VALUES WITH (modulus 16, remainder 15)
TABLESPACE pg_default;

ALTER TABLE IF EXISTS public."股票技术指标_p15"
    OWNER to postgres;


-- Table: public.行业技术指标

-- DROP TABLE IF EXISTS public."行业技术指标";

CREATE TABLE IF NOT EXISTS public."行业技术指标"
(
    "行业名称" character varying(100) COLLATE pg_catalog."default" NOT NULL,
    "日期" date NOT NULL,
    "SMA5" double precision,
    "SMA10" double precision,
    "SMA20" double precision,
    "SMA60" double precision,
    "EMA12" double precision,
    "EMA26" double precision,
    "DIF" double precision,
    "DEA" double precision,
    "MACD_hist" double precision,
    "RSI6" double precision,
    "RSI12" double precision,
    "RSI24" double precision,
    "BBANDS_UPPER" double precision,
    "BBANDS_MIDDLE" double precision,
    "BBANDS_LOWER" double precision,
    "KDJ_K" double precision,
    "KDJ_D" double precision,
    "KDJ_J" double precision,
    "VOL_MA5" double precision,
    "VOL_MA10" double precision,
    "WR14" double precision,
    "CCI14" double precision,
    "PDI14" double precision,
    "MDI14" double precision,
    "ADX14" double precision,
    "ROC6" double precision,
    "ROC12" double precision,
    "BIAS6" double precision,
    "BIAS12" double precision,
    "BIAS24" double precision,
    "OBV" double precision,
    "OBV_MA5" double precision,
    "OBV_MA10" double precision,
    CONSTRAINT "行业技术指标_pkey" PRIMARY KEY ("行业名称", "日期"),
    CONSTRAINT "行业技术指标_fkey" FOREIGN KEY ("行业名称", "日期")
        REFERENCES public."行业历史行情" ("行业名称", "日期") MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE CASCADE
)

TABLESPACE pg_default;

ALTER TABLE IF EXISTS public."行业技术指标"
    OWNER to postgres;
-- Index: idx_行业技术指标_日期

-- DROP INDEX IF EXISTS public."idx_行业技术指标_日期";

CREATE INDEX IF NOT EXISTS "idx_行业技术指标_日期"
    ON public."行业技术指标" USING btree
    ("日期" ASC NULLS LAST)
    TABLESPACE pg_default;


-- Table: public.指数技术指标

-- DROP TABLE IF EXISTS public."指数技术指标";

CREATE TABLE IF NOT EXISTS public."指数技术指标"
(
    "指数代码" character varying(10) COLLATE pg_catalog."default" NOT NULL,
    "日期" date NOT NULL,
    "SMA5" double precision,
    "SMA10" double precision,
    "SMA20" double precision,
    "SMA60" double precision,
    "EMA12" double precision,
    "EMA26" double precision,
    "DIF" double precision,
    "DEA" double precision,
    "MACD_hist" double precision,
    "RSI6" double precision,
    "RSI12" double precision,
    "RSI24" double precision,
    "BBANDS_UPPER" double precision,
    "BBANDS_MIDDLE" double precision,
    "BBANDS_LOWER" double precision,
    "KDJ_K" double precision,
    "KDJ_D" double precision,
    "KDJ_J" double precision,
    "VOL_MA5" double precision,
    "VOL_MA10" double precision,
    "WR14" double precision,
    "CCI14" double precision,
    "PDI14" double precision,
    "MDI14" double precision,
    "ADX14" double precision,
    "ROC6" double precision,
    "ROC12" double precision,
    "BIAS6" double precision,
    "BIAS12" double precision,
    "BIAS24" double precision,
    "OBV" double precision,
    "OBV_MA5" double precision,
    "OBV_MA10" double precision,
    CONSTRAINT "指数技术指标_pkey" PRIMARY KEY ("指数代码", "日期"),
    CONSTRAINT "指数技术指标_fkey" FOREIGN KEY ("指数代码", "日期")
        REFERENCES public."指数历史行情" ("指数代码", "日期") MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE CASCADE
)

TABLESPACE pg_default;

ALTER TABLE IF EXISTS public."指数技术指标"
    OWNER to postgres;
-- Index: idx_指数技术指标_日期

-- DROP INDEX IF EXISTS public."idx_指数技术指标_日期";

CREATE INDEX IF NOT EXISTS "idx_指数技术指标_日期"
    ON public."指数技术指标" USING btree
    ("日期" ASC NULLS LAST)
    TABLESPACE pg_default;