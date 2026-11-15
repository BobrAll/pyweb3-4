# Архитектура экспериментального стенда

Все экспериментальные компоненты выполняются в контейнерах. Сведения о хосте
собираются до запуска. Swift используется только как дополнительный эталон
соответствия переноса, а не как зависимость основного эксперимента.

```mermaid
flowchart LR
  C[JSON config + seed] --> R[Runner: randomized paired plan]
  G[Synthetic observation generator] -->|materialize before timing| R
  V[Deskhand Swift excerpt + SHA-256] -. parity test .-> S
  subgraph Docker bench: 2 CPU / 1 GiB / network none
    R -->|fresh subprocess per run| S[Python history policy: full / bounded]
    S --> M[perf_counter_ns + byte count + invariant oracle]
  end
  M --> D[Raw per-step JSON + per-run manifest]
  D --> A[Docker analysis: paired bootstrap / sign-flip / Holm]
  A --> F[Tables + boxplot + ECDF + stability]
  D --> H[SHA-256 archive]
```

Измерение `policy_ms` охватывает только вызов SUT. Генерация, IPC, измерение
байтов и проверка инвариантов в это время не включены. Сеть отключена.
