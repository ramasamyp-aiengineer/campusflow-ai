"""Sample and builtin RSS fixtures for Campus Signals."""

BUILTIN_URL = "builtin:campus-engineering-briefing"
ML_URL = "builtin:machine-learning"

BRIEFING_XML = """<?xml version="1.0"?>
<rss version="2.0"><channel>
<item>
  <title>Campus product teams are hiring SDE-1 backend engineers who can defend SQL joins</title>
  <link>https://www.geeksforgeeks.org/sql-join-set-1-inner-left-right-and-full-joins/</link>
  <guid>brief-hiring-sql</guid>
  <pubDate>Wed, 18 Nov 2026 09:00:00 GMT</pubDate>
  <source>Mint Campus</source>
  <description>Hiring managers asked interns to explain an outer join and a failed transaction. The tone is an opportunity for students who can show evidence, not just a CGPA.</description>
</item>
<item>
  <title>Linux 6.x scheduler change reduces tail latency for student lab VMs</title>
  <link>https://lwn.net/Articles/825584/</link>
  <guid>brief-linux</guid>
  <pubDate>Tue, 17 Nov 2026 14:00:00 GMT</pubDate>
  <source>LWN</source>
  <description>The new scheduler improved interactive latency. Kernel developers called the patch a measured growth in fairness, with a warning about rare deadlock reports.</description>
</item>
<item>
  <title>Query planners now explain hash joins in plain language</title>
  <link>https://www.postgresql.org/docs/current/planner-optimizer.html</link>
  <guid>brief-query</guid>
  <pubDate>Tue, 17 Nov 2026 11:20:00 GMT</pubDate>
  <source>Postgres Weekly</source>
  <description>A database release improved how a query planner describes index choice. It is a useful launch for students still learning SQL.</description>
</item>
<item>
  <title>Gemini structured output reaches more campus GenAI electives</title>
  <link>https://ai.google.dev/gemini-api/docs/structured-output</link>
  <guid>brief-gemini</guid>
  <pubDate>Mon, 16 Nov 2026 10:00:00 GMT</pubDate>
  <source>Google Developers</source>
  <description>The model launch adds JSON schemas for LLM coursework. Faculty called it an opportunity, with a warning that unvalidated output is still a risk.</description>
</item>
<item>
  <title>Service firms freeze campus placement offers after layoffs and a revenue loss</title>
  <link>https://en.wikipedia.org/wiki/Campus_placement</link>
  <guid>brief-placement-freeze</guid>
  <pubDate>Mon, 16 Nov 2026 15:30:00 GMT</pubDate>
  <source>Placement Pulse</source>
  <description>Two service companies paused SDE offers for the coming drive. Placement officers told students to bring verified backend projects, not just grades.</description>
</item>
<item>
  <title>City derby ends in a draw after extra time</title>
  <link>https://en.wikipedia.org/wiki/Association_football</link>
  <guid>brief-sport</guid>
  <pubDate>Mon, 16 Nov 2026 18:00:00 GMT</pubDate>
  <source>Sports Desk</source>
  <description>The football derby drew a record crowd at the city stadium.</description>
</item>
<item>
  <title>Canteen adds a monsoon special thali</title>
  <link>https://en.wikipedia.org/wiki/Thali</link>
  <guid>brief-canteen</guid>
  <pubDate>Sun, 15 Nov 2026 06:00:00 GMT</pubDate>
  <source>Campus Diary</source>
  <description>The hostel canteen menu changed for the week. Students can collect tokens at lunch.</description>
</item>
<item>
  <title>FastAPI services face a rate-limit outage after a leaked key</title>
  <link>https://fastapi.tiangolo.com/tutorial/security/first-steps/</link>
  <guid>brief-fastapi-outage</guid>
  <pubDate>Wed, 18 Nov 2026 08:10:00 GMT</pubDate>
  <source>The Hindu Tech</source>
  <description>A campus API leaked an API key and suffered an outage. The failure mode is a cautionary breach for anyone shipping Python services.</description>
</item>
</channel></rss>
"""

ML_XML = """<?xml version="1.0"?>
<rss version="2.0"><channel>
<item>
  <title>A campus lab trains a small neural model on handwritten digits</title>
  <link>https://en.wikipedia.org/wiki/MNIST_database</link>
  <guid>ml-digits</guid>
  <pubDate>Wed, 18 Nov 2026 09:30:00 GMT</pubDate>
  <source>Campus ML Notes</source>
  <description>Students trained a neural network on a public digit dataset. The write-up calls the result a useful launch for anyone starting machine learning, and warns that a tiny training set still overfits.</description>
</item>
<item>
  <title>Hiring teams ask interns to explain a training split before the model</title>
  <link>https://scikit-learn.org/stable/modules/cross_validation.html</link>
  <guid>ml-hiring</guid>
  <pubDate>Tue, 17 Nov 2026 12:00:00 GMT</pubDate>
  <source>Mint Campus</source>
  <description>Machine learning internships now start with the training and test split. Recruiters called it an opportunity for students who can defend the dataset, not only the accuracy number.</description>
</item>
<item>
  <title>City derby ends in a draw after extra time</title>
  <link>https://en.wikipedia.org/wiki/Association_football</link>
  <guid>ml-derby</guid>
  <pubDate>Mon, 16 Nov 2026 18:00:00 GMT</pubDate>
  <source>Sports Desk</source>
  <description>The football derby drew a crowd and ended level after extra time.</description>
</item>
</channel></rss>
"""

WIRE_URL = "builtin:ai-research-wire"
WIRE_XML = """<?xml version="1.0"?>
<rss version="2.0"><channel>
<item>
  <title>Students train a small neural model to read handwritten digits</title>
  <link>https://pytorch.org/tutorials/beginner/basics/data_tutorial.html</link>
  <guid>wire-digits</guid>
  <pubDate>Wed, 18 Nov 2026 11:00:00 GMT</pubDate>
  <source>AI Research Wire</source>
  <description>A student team trained a compact neural network on a public digit dataset and published the training notebook.</description>
</item>
<item>
  <title>Interns now explain the training split before the model, hiring teams say</title>
  <link>https://en.wikipedia.org/wiki/Training,_validation,_and_test_data_sets</link>
  <guid>wire-interns</guid>
  <pubDate>Tue, 17 Nov 2026 15:00:00 GMT</pubDate>
  <source>Hacker Digest</source>
  <description>Machine learning interviews start with the training and test split. Recruiters see it as an opportunity for students who can defend a dataset.</description>
</item>
<item>
  <title>LoRA quantization cuts VRAM usage by 40 percent for fine-tuning</title>
  <link>https://huggingface.co/docs/peft/conceptual_guides/lora</link>
  <guid>wire-lora</guid>
  <pubDate>Wed, 18 Nov 2026 07:00:00 GMT</pubDate>
  <source>Model Lab Notes</source>
  <description>A 4-bit LoRA recipe cut GPU memory by 40 percent while keeping model accuracy close to full fine-tuning. Researchers called it a breakthrough for campus labs with small GPUs.</description>
</item>
<item>
  <title>Entry-level AI hiring freeze brings layoffs as teams ask for RAG evaluation skills</title>
  <link>https://python.langchain.com/docs/tutorials/rag/</link>
  <guid>wire-rag-hiring</guid>
  <pubDate>Tue, 17 Nov 2026 09:00:00 GMT</pubDate>
  <source>Placement Pulse</source>
  <description>Several startups paused fresher hiring after layoffs. The roles that remain ask for RAG evaluation and agentic workflows, and for candidates who can test a retrieval model.</description>
</item>
<item>
  <title>Stock market closes higher on festive demand</title>
  <link>https://en.wikipedia.org/wiki/Stock_market</link>
  <guid>wire-markets</guid>
  <pubDate>Mon, 16 Nov 2026 16:00:00 GMT</pubDate>
  <source>Market Desk</source>
  <description>Indices rose on retail demand during the festival week.</description>
</item>
</channel></rss>
"""

BUILTIN_FEEDS = {
    BUILTIN_URL: BRIEFING_XML,
    ML_URL: ML_XML,
    WIRE_URL: WIRE_XML,
}
