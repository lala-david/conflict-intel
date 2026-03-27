<div align="center">

# Terror Researcher

**Automated Daily Terror Intelligence System**

전 세계 테러 사건, 위협 동향, 제재 변동을 자동으로 수집·분석하는 인텔리전스 엔진

</div>

---

## 배경

테러 위협은 예고 없이 발생하고, 관련 정보는 ACLED, GDELT, OFAC, UN 제재 목록, 싱크탱크 분석, 뉴스 등 수십 개 채널에 흩어져 있다. 매일 수백 건의 분쟁 이벤트와 수십 편의 전문가 분석이 쏟아지지만, 이를 종합하여 위협 수준을 판단하고 패턴을 읽어내는 건 전문 인력이 아니면 불가능하다. 이 시스템은 13개 소스에서 데이터를 자동 수집하고, LLM이 전문 인텔리전스 브리프 형식으로 분석하여 매일 GitHub에 자동 커밋한다. BLUF(Bottom Line Up Front) 원칙, 신뢰도 등급, EUROPOL TE-SAT 분류 체계를 적용한 전문 분석 리포트를 한글/영문 듀얼로 생성한다.

---

## 무엇을 추적하는가

- **사건 데이터** — 폭탄 공격, IED, 자살 공격, 무장 습격, 드론/미사일 공격 (ACLED + GDELT)
- **조직 동향** — ISIS, Al-Qaeda, 헤즈볼라, 탈레반, 지역 무장단체 활동 패턴
- **지역별 위협** — 중동, 아프리카, 남아시아, 유럽, 북미 위협 수준 평가
- **제재 변동** — OFAC SDN, UN 안보리, EU 제재 목록 신규/변경 추적
- **전문가 분석** — Long War Journal, Soufan Center, CTC Sentinel, Jamestown 등 전문 기관 리서치
- **정책 변화** — 대테러 법안, 국제 협력, 규제 동향

---

## Architecture

```mermaid
flowchart TB
    subgraph sources["Data Sources (13)"]
        direction LR
        gdelt["GDELT\n(실시간 이벤트)"]
        acled["ACLED\n(코딩된 사건)"]
        gnews["Google News\n(테러 뉴스)"]
        rss["Expert RSS\n(4개 기관)"]
        sanctions["OpenSanctions\n(제재 통합)"]
        ofac["OFAC\n(미국 제재)"]
    end

    subgraph process["Processing"]
        filter["테러 관련 필터링\n(키워드 + CAMEO 코드)"]
        dedup["중복 제거"]
    end

    subgraph analyze["LLM Analysis"]
        llm["GPT-5.4-mini\ntemp: 0.12"]
        framework["BLUF 원칙\n신뢰도 등급\nTE-SAT 분류"]
        llm --- framework
    end

    subgraph output["Daily Brief"]
        ko["KO Report\n한글 브리프"]
        en["EN Report\nEnglish Brief"]
        raw["Raw JSON"]
    end

    sources --> process --> analyze --> output

    style sources fill:#8b0000,stroke:#333,color:#fff
    style process fill:#b22222,stroke:#333,color:#fff
    style analyze fill:#1a1a2e,stroke:#333,color:#eee
    style output fill:#2d2d2d,stroke:#8b0000,color:#eee
```

---

## 분석 프레임워크

```mermaid
mindmap
  root((Terror Intel))
    BLUF
      위협 판단
      신뢰도 등급
      핵심 시그널
    Regional Analysis
      Middle East / MENA
      Sub-Saharan Africa
      South / SE Asia
      Europe / North America
    Threat Groups
      ISIS / ISIL
      Al-Qaeda Network
      Iran Proxies
      Regional Militants
    Sanctions
      OFAC SDN
      UN Security Council
      EU Restrictive Measures
    Classification
      Jihadist
      Right-wing
      Left-wing
      Ethno-nationalist
      Single-issue
```

---

## 데이터 소스

```mermaid
flowchart LR
    subgraph tier1["Core — 사건 데이터"]
        A["GDELT\n15분 업데이트"]
        B["ACLED API\n주간 업데이트"]
        C["Google News\n실시간"]
    end

    subgraph tier2["Analysis — 전문 기관"]
        D["Long War Journal"]
        E["Soufan Center"]
        F["CTC Sentinel"]
        G["Jamestown"]
    end

    subgraph tier3["Sanctions — 제재 추적"]
        H["OpenSanctions\n329개 소스 통합"]
        I["OFAC SDN"]
        J["UN SC List"]
    end

    style tier1 fill:#8b0000,stroke:#333,color:#fff
    style tier2 fill:#2d2d2d,stroke:#333,color:#eee
    style tier3 fill:#1a1a2e,stroke:#333,color:#eee
```

---

<div align="center">

*Automated terror intelligence — so analysts can focus on judgment, not collection.*

</div>
