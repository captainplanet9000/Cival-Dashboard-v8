# MemGPT / Letta Client Research Summary

This document summarizes the key findings regarding the integration of MemGPT's successor, Letta, for memory capabilities in the `python-ai-services` project.

## Key Findings:

1.  **Project Renaming:**
    *   The original open-source project `MemGPT` has evolved. The core technology is now referred to as `Letta`.
    *   The official Python client SDK for interacting with a Letta server is `letta-client`.

2.  **Installation:**
    *   The client SDK can be installed using pip:
        ```bash
        pip install letta-client
        ```
    *   This dependency has been added to `requirements.txt`.

3.  **Architecture for Integration:**
    *   The `python-ai-services` application, specifically a planned `MemoryService`, will act as a client to a separately running Letta Server process.
    *   This means `python-ai-services` will not embed the Letta agent's core logic directly but will communicate with the Letta server via an API using the `letta-client` SDK.

4.  **Letta Server Persistence (Original Points):**
    *   **Database:** The Letta Server uses PostgreSQL for its persistence layer. This is configured via the `LETTA_PG_URI` environment variable on the Letta server side.
    *   **Supabase Compatibility:** This PostgreSQL requirement makes it compatible with Supabase, as Supabase provides standard PostgreSQL databases. The `LETTA_PG_URI` for the Letta server can be pointed to a Supabase PostgreSQL instance.
    *   **Data Management by Letta Server:** The Letta Server is responsible for managing its own database schema within the configured PostgreSQL database. This includes tables for agent state, configuration, core memory (like event streams and working context), and archival/vector memory (often utilizing pgvector if the PostgreSQL instance has the extension and Letta is configured accordingly).

## Persistence Mechanism & Implications for Custom Connectors

This section clarifies how Letta's persistence works and why a custom Python storage connector within `python-ai-services` is generally not required for Letta's primary memory functions.

*   **Server-Side Persistence:** As stated above, the Letta Server directly connects to and manages its data within a PostgreSQL database (our Supabase instance) using the `LETTA_PG_URI` environment variable. This is a core feature of the Letta Server.

*   **No Custom Python Connector Needed for Core Letta Memory:**
    *   The `python-ai-services` application, particularly the `MemoryService`, interacts with Letta agents through the `letta-client` SDK. This SDK communicates with the Letta Server API.
    *   The Letta Server itself handles all database operations related to its agents' memories (creating tables, writing messages, recalling information, managing embeddings for vector search, etc.).
    *   Therefore, `MemoryService` does **not** need to implement a custom Supabase/pgvector storage connector for these primary MemGPT/Letta memory functions. The `letta-client` abstracts these interactions.

*   **Implications for `AgentPersistenceService` and `agent_memories` Table:**
    *   The existing `agent_memories` table (defined by `AgentPersistenceService`'s DDL, potentially using pgvector) was designed for a scenario where `python-ai-services` might manage agent memories more directly.
    *   It is highly unlikely that the Letta Server will automatically use or integrate with this specific, pre-existing `agent_memories` table. Letta will create and manage its own set of tables according to its internal schema.
    *   Consequently, for agents whose memory is fully managed by Letta, our `agent_memories` table might become redundant for *direct Letta memory storage*.
    *   Potential alternative uses for the `agent_memories` table could be:
        *   Storing memories for other types of agents within `python-ai-services` that do *not* use Letta.
        *   Acting as a supplementary long-term storage or a custom cross-agent knowledge base, distinct from Letta's operational memory.
        *   Storing embeddings or metadata for large datasets that might be loaded into Letta agents as "sources" or external documents, if Letta's document loading features don't cover all needs.
        *   Storing mappings between `app_agent_id` and `letta_agent_id` if this isn't easily queryable or managed via Letta Server's API by name alone (though naming conventions like `app_agent_{app_agent_id}` are planned for Letta agent names).

*   **Resolution of Original "Implement Supabase Storage Connector" Step:**
    *   The original MemGPT integration plan included a step like "Implement Supabase Storage Connector."
    *   This step is effectively resolved by correctly configuring the **Letta Server** to use our Supabase PostgreSQL database via `LETTA_PG_URI`. The "connector" is part of the Letta Server itself, not something `MemoryService` needs to build in Python for Letta's internal memory.

5.  **Python SDK (`letta-client`):**
    *   **Instantiation:** The client is typically instantiated as follows:
        ```python
        from letta import Letta
        # Default Letta server port is 8283
        letta_client = Letta(base_url="http://<letta_server_host>:<port>")
        ```
        The `<letta_server_host>` and `<port>` will need to be configurable for `python-ai-services`.
    *   **Core Functionality (Expected):**
        *   **Agent Management:** The SDK provides APIs for creating, listing, getting details of, and deleting Letta agents. Each Letta agent has its own isolated memory.
        *   **Interaction:** Sending messages (which can be user queries, observations, or system messages) to a specific Letta agent. The Letta server and agent then process these messages, update internal memory, and can generate responses.
        *   The `letta-client` abstracts the direct HTTP API calls to the Letta server.

6.  **Core Interaction Pattern for `MemoryService`:**
    *   The `MemoryService` within `python-ai-services` will use the `letta-client` SDK.
    *   For CrewAI agents that require persistent memory or advanced recall capabilities, `MemoryService` will:
        *   Potentially create or assign a dedicated Letta agent instance per CrewAI agent or per crew/task context using a consistent naming convention.
        *   Forward relevant messages, tool outputs, or observations from the CrewAI workflow to the designated Letta agent via `letta-client`.
        *   Query the Letta agent (again, via `letta-client`) to retrieve relevant memories or context when needed by a CrewAI agent to inform its actions.

## Next Steps & Further Exploration:

*   **Detailed API/SDK Exploration:** During the implementation of `MemoryService`, a more detailed look at `letta-client`'s specific methods will be necessary. This includes:
    *   Exact methods for sending different types of messages/data to a Letta agent.
    *   Methods for querying an agent's memory (e.g., by similarity, specific recall).
    *   How responses or recalled memories are structured when returned by the SDK.
*   **Letta Server Deployment:** A deployment strategy for the Letta Server itself will be needed. This server process must run alongside `python-ai-services` and be accessible to it. It will also need its `LETTA_PG_URI` configured to point to the chosen PostgreSQL database (e.g., the Supabase DB).
*   **Error Handling and Resilience:** Strategies for handling potential unavailability of the Letta server or errors from the `letta-client` API calls will be important for `MemoryService`.

This summary provides the foundational knowledge for proceeding with the integration of `letta-client` for advanced memory features.
