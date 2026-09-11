-- ============================================
-- FTD Analytics — Modelo Dimensional (Esquema Estrela)
-- ============================================

CREATE TABLE Dim_Obra (
    obra_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    obra_nome   TEXT UNIQUE NOT NULL
);

CREATE TABLE Dim_Credor (
    credor_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    credor_nome TEXT UNIQUE NOT NULL
);

CREATE TABLE Dim_Mes (
    mes_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    competencia TEXT UNIQUE NOT NULL,   -- formato AAAA-MM
    ano         INTEGER NOT NULL,
    mes         INTEGER NOT NULL
);

CREATE TABLE Dim_Tipo_Erro (
    tipo_erro_id INTEGER PRIMARY KEY AUTOINCREMENT,
    tipo_erro    TEXT UNIQUE NOT NULL
);

CREATE TABLE Fato_Lancamentos (
    fato_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    lancamento_num INTEGER NOT NULL,
    obra_id        INTEGER NOT NULL REFERENCES Dim_Obra(obra_id),
    credor_id      INTEGER NOT NULL REFERENCES Dim_Credor(credor_id),
    mes_id         INTEGER NOT NULL REFERENCES Dim_Mes(mes_id),
    valor          REAL,
    status         TEXT NOT NULL CHECK (status IN ('com erro','sem erro'))
);

-- Tabela-ponte: um lançamento pode ter 0, 1 ou vários tipos de erro
CREATE TABLE Fato_Lancamento_Erro (
    fato_id      INTEGER NOT NULL REFERENCES Fato_Lancamentos(fato_id),
    tipo_erro_id INTEGER NOT NULL REFERENCES Dim_Tipo_Erro(tipo_erro_id),
    PRIMARY KEY (fato_id, tipo_erro_id)
);

CREATE INDEX idx_fato_obra   ON Fato_Lancamentos(obra_id);
CREATE INDEX idx_fato_credor ON Fato_Lancamentos(credor_id);
CREATE INDEX idx_fato_mes    ON Fato_Lancamentos(mes_id);
