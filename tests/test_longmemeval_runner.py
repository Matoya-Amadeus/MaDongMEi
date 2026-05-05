#!/usr/bin/env python3
from __future__ import annotations
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
REPO_ROOT = Path(__file__).resolve().parent.parent
RUNNER_PATH = REPO_ROOT / "scripts" / "longmemeval_madongmei_runner.py"
SUITE_PATH = REPO_ROOT / "scripts" / "longmemeval_benchmark_suite.py"
EXACT_HEAD_ONLY_RESIDUAL_CASES = [
    (
        "How many Italian restaurants have I tried?",
        [
            "I visited County Clare and the French Quarter on vacation.",
            "I tried three different Korean restaurants and Korean style BBQ.",
            "I tried four different Indian and Middle Eastern cuisines.",
        ],
        {1, 2},
    ),
    (
        "What day of the week do I take a cocktail making class?",
        [
            "I'm exploring vegetarian cuisine and coffee shops.",
            "My cocktail making class on Fridays covers margaritas and tequila.",
            "I moved my cocktail making class on Thursday once.",
        ],
        {1, 2},
    ),
    (
        "How many bikes do I currently own?",
        [
            "I read about meditation techniques and reducing plastic waste.",
            "I currently have three bikes: road, mountain, and commuter.",
            "I bought a new hybrid bike after selling my old folding bike.",
        ],
        {1, 2},
    ),
    (
        "How often do I attend yoga classes to help with my anxiety?",
        [
            "I planned a family vacation and set up 1Password.",
            "I attend yoga classes three times a week for self-care.",
            "I used to go twice a week before the class schedule changed.",
        ],
        {1, 2},
    ),
    (
        "How old was I when I moved to the United States?",
        [
            "I read about the green card application process.",
            "I'm a 32 year old from India living in the United States for the past five years.",
            "My master's degree and work visa paperwork were stressful.",
        ],
        {1, 2},
    ),
    (
        "Which happened first, the persistent cough or the skin tag removal?",
        [
            "I added new plants to the garden.",
            "I had a persistent cough for the past three weeks and the doctor diagnosed bronchitis.",
            "I later scheduled an appointment to remove a skin tag.",
        ],
        {1, 2},
    ),
    (
        "What time do I wake up on Tuesdays and Thursdays?",
        [
            "I collected healthy breakfast ideas.",
            "On Tuesdays and Thursdays I'm waking up 15 minutes earlier.",
            "My morning routine usually has me waking up at 7 00 am.",
        ],
        {1, 2},
    ),
    (
        "Which came first, Rack Fest did I participate in the Turbocharged Tuesdays?",
        [
            "I'm comparing car wax products.",
            "I joined Turbocharged Tuesdays on June 14th with my Mustang GT.",
            "I participated in Rack Fest on June 18th.",
        ],
        {1, 2},
    ),
    (
        "Which came first, the Effective Time Management workshop or the Data Analysis using Python webinar?",
        [
            "I tried to reduce social media distractions.",
            "I attended the Effective Time Management workshop two months ago.",
            "I participated in a Data Analysis using Python webinar.",
        ],
        {1, 2},
    ),
    (
        "Which happened first, PlankChallenge or my post about vegan chili recipe?",
        [
            "I collected meal prep ideas.",
            "I posted my PlankChallenge today on Instagram.",
            "I shared a recipe for vegan chili using FoodieAdventures.",
        ],
        {1, 2},
    ),
    (
        "How long was it from when I launch my website when I signed a contract with my first client?",
        [
            "I attended a marketing workshop.",
            "I launched my website for my freelance business.",
            "I signed a contract with my first client after finishing the business plan outline.",
        ],
        {1, 2},
    ),
    (
        "How much time passed between my undergraduate degree and the submission of my master's thesis?",
        [
            "I took a deep learning online course.",
            "I completed my undergraduate degree in computer science in May.",
            "I submitted my master's thesis on computer science in November.",
        ],
        {1, 2},
    ),
    (
        "How many days passed between when I finished reading The Nightingale and the day I started reading The Hitchhiker's Guide?",
        [
            "I looked for graphic novels.",
            "I finished reading The Nightingale by Kristin Hannah.",
            "I started reading The Hitchhiker's Guide by Douglas Adams.",
        ],
        {1, 2},
    ),
    (
        "How long was it between the Museum of Modern Art MoMA and the Ancient Civilizations exhibit?",
        [
            "I studied Fauvism.",
            "I joined a Museum of Modern Art MoMA tour.",
            "I visited the Ancient Civilizations exhibit at the Metropolitan Museum of Art.",
        ],
        {1, 2},
    ),
    (
        "How much earlier do I wake up on Fridays compared to other weekdays?",
        [
            "I changed my daily commute.",
            "I'm waking up at 6 30 am on weekdays.",
            "On Fridays I like to get a head start and wake up at 6 00 am.",
        ],
        {1, 2},
    ),
    (
        "How much faster did I finish the 5K run compared to my previous year?",
        [
            "I volunteered at a bake sale.",
            "I finished a 5K run last year in 45 minutes.",
            "I recently finished a 5K in 35 minutes.",
        ],
        {1, 2},
    ),
    (
        "How much did I save on the Jimmy Choo heels?",
        [
            "I bought new sunglasses.",
            "The Jimmy Choo heels originally retailed for 500.",
            "I got the Jimmy Choo heels at the outlet mall for 200.",
        ],
        {1, 2},
    ),
    (
        "How much did I spend on car wash and parking ticket?",
        [
            "I got my bike serviced.",
            "The car wash on February 3rd cost 15.",
            "I got a parking ticket on January 5th near my work for 50.",
        ],
        {1, 2},
    ),
    (
        "How much cashback did I earn at SaveMart last Thursday?",
        [
            "I shopped at Walmart and donated to clean water.",
            "I spent 75 on groceries at SaveMart last Thursday.",
            "My membership lets me earn 1 cashback on purchases.",
        ],
        {1, 2},
    ),
    (
        "How many social media breaks in total did I take?",
        [
            "I watched the Dodgers game.",
            "I took a week long break from social media in January.",
            "I took a 10 day break to cut down on social media in February.",
        ],
        {1, 2},
    ),
    (
        "How many weddings have I attended in this year?",
        [
            "I went to cousin Rachel's wedding at a vineyard.",
            "I attended Emily and Sarah's rooftop wedding.",
            "I'm looking for date ideas for this weekend.",
            "I need a content calendar template.",
            "How do Gurkhas traditionally celebrate weddings?",
            "I joined a charity walk.",
            "I wore a silver locket to a cousin's wedding.",
            "I need singing warm-up tips.",
            "I just got back from Jen and Tom's barn wedding.",
        ],
        {0, 1, 8},
    ),
]

EXACT_TOP10_RESIDUAL_CASES = [
    (
        "How many minutes did I exceed my target time by in the marathon?",
        [
            "I planned volleyball league workouts and swimming lessons.",
            "My target time for the marathon was 4 hours and 10 minutes.",
            "I completed my first full marathon in 4h 22min.",
        ],
        {1, 2},
    ),
    (
        "How many graduation ceremonies have I attended in the past three months?",
        [
            "I read a treaty of Westphalia history summary.",
            "I attended Emma's preschool graduation about two months ago.",
            "I went to Rachel's master's degree graduation ceremony.",
            "I attended my alma mater's annual alumni reunion.",
            "I attended colleague Alex's graduation from a leadership program.",
        ],
        {1, 2, 3, 4},
    ),
    (
        "How many hours in total did I spend driving to my three road trip destinations combined?",
        [
            "I tracked charity contributions for the year.",
            "My Outer Banks in North Carolina road trip took four hours to drive.",
            "I drove six hours to Washington D C recently.",
            "I drove for five hours to the mountains in Tennessee.",
        ],
        {1, 2, 3},
    ),
    (
        "How many model kits have I worked on or bought?",
        [
            "I bought laptop accessories at Best Buy.",
            "I finished a Revell F 15 Eagle kit.",
            "I painted a Tamiya 1 48 scale Spitfire model kit.",
            "I worked on a 1 16 scale German Tiger I tank diorama.",
            "I got a 1 72 scale B 29 bomber and a 69 Camaro at a model show.",
        ],
        {1, 2, 3, 4},
    ),
    (
        "Which pair of shoes did I clean last month?",
        [
            "I spent 75 on groceries at SaveMart.",
            "I compared Merrell Moab 2 Mid Waterproof and Keen Targhee II Mid WP hiking boots.",
            "I cleaned my spare running shoes after the trail trip.",
        ],
        {1, 2},
    ),
    (
        "How many magazine subscriptions do I currently have?",
        [
            "I got a book subscription box with a thriller novel.",
            "I subscribed to the New Yorker magazine.",
            "I am getting Architectural Digest for home decor inspiration.",
            "I canceled my Forbes magazine subscription.",
            "I bought my last National Geographic issue on March 15th.",
        ],
        {1, 2, 3, 4},
    ),
    (
        "How many different cuisines have I learned to cook or tried out in the past few months?",
        [
            "I read about top rated restaurants in Portland.",
            "I attended a class on vegan cuisine.",
            "I learned chicken tikka masala.",
            "I tried Korean bibimbap from a cooking class recipe.",
            "I tried an Ethiopian restaurant in town.",
        ],
        {1, 2, 3, 4},
    ),
    (
        "What is the order of the concerts and musical events I attended in the past two months, starting from the earliest?",
        [
            "I watched Stranger Things last night.",
            "I went to a Billie Eilish concert in Philly.",
            "I attended a music festival in Brooklyn.",
            "I saw Queen live with Adam Lambert.",
            "I attended a free outdoor concert series.",
            "I went to a jazz night at a local bar.",
        ],
        {1, 2, 3, 4, 5},
    ),
    (
        "What is the total amount of money I earned from selling my products at the markets?",
        [
            "I planned an Instagram giveaway.",
            "I sold 12 bunches of herbs at the harvest festival market.",
            "I sold 15 jars of homemade products.",
            "I sold 20 potted herb plants at the summer solstice market.",
        ],
        {1, 2, 3},
    ),
    (
        "How many different museums or galleries did I visit in the month of February?",
        [
            "I read about cultural institutions in Swansea.",
            "I took my niece to the Natural History Museum on 2 8.",
            "I visited the Art Cube on 2 15.",
            "I attended a guided workshop at the Modern Art Museum.",
        ],
        {1, 2, 3},
    ),
    (
        "Which social media platform did I gain the most followers on over the past month?",
        [
            "I optimized my live streaming setup.",
            "My Instagram followers increased this month.",
            "My YouTube views and followers also grew.",
            "My TikTok followers grew the fastest.",
        ],
        {1, 2, 3},
    ),
    (
        "Which group did I join first, 'Page Turners' or 'Marketing Professionals'?",
        [
            "I bought a phone case.",
            "I joined Page Turners book club.",
            "I joined Marketing Professionals for networking.",
        ],
        {1, 2},
    ),
    (
        "Who did I go with to the music event last Saturday?",
        [
            "I planned a trip to LA.",
            "I went to the Queen concert with my parents.",
            "I attended a music festival in Brooklyn with a group of friends.",
            "I found talent at a free outdoor concert series.",
        ],
        {1, 2, 3},
    ),
    (
        "How many different doctors did I visit?",
        [
            "I watched Stranger Things.",
            "Dr Smith, my primary care physician, prescribed antibiotics for a UTI.",
            "ENT specialist Dr Patel diagnosed chronic sinusitis.",
            "Dermatologist Dr Lee did a biopsy.",
        ],
        {1, 2, 3},
    ),
    (
        "Which three events happened in the order from first to last: the day I helped my friend prepare the nursery, the day I helped my cousin pick out stuff for her baby shower, and the day I ordered a customized phone case for my friend's birthday?",
        [
            "I took a comedy workshop.",
            "I helped my friend prepare a nursery.",
            "I helped my cousin pick out some stuff for her baby shower.",
            "I ordered a customized phone case for my friend's birthday.",
        ],
        {1, 2, 3},
    ),
    (
        "How many different types of citrus fruits have I used in my cocktail recipes?",
        [
            "I brewed a coffee blend.",
            "I made orange bitters.",
            "I used fresh lime juice in a classic daiquiri.",
            "I added grapefruit to a paloma cocktail.",
        ],
        {1, 2, 3},
    ),
    (
        "How many rare items do I have in total?",
        [
            "I am starting a collection of rare items.",
            "I have 57 rare records.",
            "I collect rare books including a first edition.",
            "I appraised an antique vase.",
        ],
        {1, 2, 3},
    ),
    (
        "How much total money have I spent on bike-related expenses since the start of the year?",
        [
            "I read about quarterback news.",
            "I bought specialized bike cleaner while tracking 347 miles.",
            "I took my bike in for a tune up on April 20th.",
            "I bought a bike rack for my car.",
        ],
        {1, 2, 3},
    ),
    (
        "How many times did I ride rollercoasters across all the events I attended from July to October?",
        [
            "I bought Avengers Endgame on Blu ray.",
            "I rode the Xcelerator rollercoaster at Knott's Berry Farm.",
            "I rode Mako Kraken and Manta at SeaWorld.",
            "I rode Space Mountain Ghost Galaxy at Disneyland.",
            "I went to Halloween Horror Nights at Universal Studios Hollywood.",
        ],
        {1, 2, 3, 4},
    ),
    (
        "How many kitchen items did I replace or fix?",
        [
            "I searched for a tennis court.",
            "I replaced my old kitchen faucet with a new Moen one.",
            "I added a new kitchen mat.",
            "I replaced the old toaster with a toaster oven.",
            "I donated my old coffee maker.",
            "I fixed the kitchen shelves.",
        ],
        {1, 2, 3, 4, 5},
    ),
    (
        "How many weeks in total do I spent on reading 'The Nightingale' and listening to 'Sapiens: A Brief History of Humankind' and 'The Power'?",
        [
            "I watched Hamilton on Disney.",
            "I started reading The Nightingale by Kristin Hannah.",
            "I finished reading The Nightingale.",
            "I listened to Sapiens A Brief History of Humankind by Yuval Noah Harari.",
            "I finished listening to The Power by Naomi Alderman.",
        ],
        {1, 2, 3, 4},
    ),
]

FALLBACK_EXACT_PREFERENCE_CASES = [
    (
        "Can you suggest some accessories that would complement my current photography setup?",
        [
            "Generic term paper research advice.",
            "Biking trails in New Zealand are scenic.",
            "I'm looking to upgrade my camera flash for my Sony A7R IV. I chose the Godox V1 and need cases, pouches, external battery packs, lens cleaning, a Gitzo tripod, and a camera bag.",
        ],
        2,
    ),
    (
        "What should I serve for dinner this weekend with my homegrown ingredients?",
        [
            "I'm looking for new cocktail recipes.",
            "Board game night recovery notes.",
            "I need recipe ideas using fresh basil and mint, and I harvested cherry tomatoes from my garden after working on pepper plants and aphids.",
        ],
        2,
    ),
    (
        "I've been thinking about making a cocktail for an upcoming get-together, but I'm not sure which one to choose. Any suggestions?",
        [
            "Smart light bulbs and storage bins.",
            "Concert tickets and wedding decorations.",
            "I was experimenting with cocktails using Hendrick's gin, a Pimm's Cup, muddled cucumber, simple syrup, and grapefruit garnish.",
        ],
        2,
    ),
    (
        "I've been having trouble with the battery life on my phone lately. Any tips?",
        [
            "London layover and live stream platform advice.",
            "Hydration and workout playlist notes.",
            "I organize tech accessories such as a portable power bank, wireless charging pad, charging cables, adapters, and extra batteries in a travel pouch.",
        ],
        2,
    ),
    (
        "I was thinking of trying a new coffee creamer recipe. Any recommendations?",
        [
            "Spring cleaning and pesto recipe notes.",
            "Photography gear packing advice.",
            "I started making my own flavored creamer with almond milk, vanilla extract, and honey to reduce my sugar intake.",
        ],
        2,
    ),
    (
        "I was thinking about rearranging the furniture in my bedroom this weekend. Any tips?",
        [
            "Wi-Fi signal troubleshooting and bike trail ideas.",
            "Chicago restaurants and car maintenance.",
            "I want mid-century modern design inspiration for a bedroom dresser from West Elm, Crate Barrel, and AllModern.",
        ],
        2,
    ),
    (
        "Can you suggest some activities that I can do in the evening?",
        [
            "Movie night and vacation recommendations.",
            "Cycling routes and project roadmap notes.",
            "I want ideas for the later part of the day, winding down by 9 30 pm, guided meditation, sleep, relaxation, and calming my mind before bed.",
        ],
        2,
    ),
]

FALLBACK_EXACT_RESIDUAL_CASES = [
    (
        "What was the the life event of one of my relatives that I participated in a week ago?",
        [
            "Family BBQ menu ideas and kid friendly food.",
            "A one-year SMART plan for first-year college students.",
            "Korean culture and language resources.",
            "Heisenberg influenced quantum mechanics.",
            "Fishing industry traditions in Newfoundland.",
            "I am getting ready to start planning my own wedding and need advice on choosing a wedding planner.",
            "I came back from Michael's engagement party at a rooftop bar and thought about my own wedding venue.",
        ],
        [
            "2023/06/22 (Thu) 18:33",
            "2023/04/12 (Wed) 06:33",
            "2023/06/07 (Wed) 03:32",
            "2023/04/25 (Tue) 13:52",
            "2023/04/24 (Mon) 15:08",
            "2023/06/15 (Thu) 10:02",
            "2023/05/06 (Sat) 18:10",
        ],
        {5, 6},
    ),
    (
        "How much time do I dedicate to practicing violin every day?",
        [
            "Gymnastics athletes practice every day.",
            "A political campaigner teaching social policy.",
            "Renewable energy technology since 2010.",
            "Hummingbirds chase prey while flying.",
            "Pesticides can endanger wildlife populations.",
            "I have been practicing guitar for 30 minutes daily while learning music theory and fingerpicking techniques.",
        ],
        None,
        {5},
    ),
    (
        "What is the name of my hamster?",
        [
            "Essential oils for home yoga practice.",
            "A suspicious looking eye and spelunker potion.",
            "The Chiefs Super Bowl win last month.",
            "Sewing machine fabric suggestions.",
            "Rollercoasters at Nagashima Spa Land.",
            "My cat's digestive health improved after a probiotic supplement, and I need a new cat litter box.",
        ],
        None,
        {5},
    ),
    (
        "What kitchen appliance did I buy 10 days ago?",
        [
            "Mortgage estimate for a new apartment.",
            "Samsung Galaxy battery life problem.",
            "A dinner party light switch ambiance.",
            "White Converse picnic shoes.",
            "California travel suggestions.",
            "I just got a smoker today and want to experiment with hickory and apple wood for meats.",
        ],
        [
            "2023/03/25 (Sat) 18:26",
            "2023/03/02 (Thu) 14:57",
            "2023/03/07 (Tue) 16:21",
            "2023/03/02 (Thu) 13:04",
            "2023/03/15 (Wed) 07:41",
            "2023/03/15 (Wed) 11:56",
        ],
        {5},
    ),
    (
        "What brand of shampoo do I currently use?",
        [
            "Razer keyboard gaming setup.",
            "Transform brand marketing services.",
            "Sephora skincare and wireless earbuds.",
            "Vintage camera storage notes.",
            "Sustainable agriculture trends.",
            "I use a lavender scented shampoo from Trader Joe's after trying exfoliating gloves and a loofah.",
        ],
        None,
        {5},
    ),
    (
        "How often do I see Dr. Johnson?",
        [
            "Stand-up comedy by John Mulaney.",
            "Gold earrings and jewelry cleaning.",
            "A road trip with my friend Chris.",
            "Restaurants near the Willis Tower.",
            "New friends online.",
            "I had a session with Dr. Smith this week and discussed setting healthy boundaries.",
            "My therapy session with Dr. Smith is every two weeks, and we talked about boundaries.",
        ],
        None,
        {5, 6},
    ),
    (
        "What was the social media activity I participated 5 days ago?",
        [
            "Stage fright before The Sound of Music.",
            "Seoul day trip suggestions.",
            "Kitten Luna flea prevention.",
            "Take That tour highlights.",
            "Eco-friendly skincare routines.",
            "I participated in a social media challenge called #PlankChallenge today during my fitness routine.",
            "I shared a vegan chili recipe using #FoodieAdventures yesterday and got lots of attention.",
        ],
        [
            "2023/03/20 (Mon) 11:50",
            "2023/02/11 (Sat) 02:46",
            "2023/03/15 (Wed) 18:51",
            "2023/02/21 (Tue) 03:16",
            "2023/03/15 (Wed) 03:15",
            "2023/03/15 (Wed) 09:07",
            "2023/03/10 (Fri) 01:55",
        ],
        {5, 6},
    ),
    (
        "How many days ago did I meet Emma?",
        [
            "Conversation starters for a charity event.",
            "Vegan German sausages recipe.",
            "AppArmor blocking Discord.",
            "Coffee brand live stream notes.",
            "Herbal teas for productivity.",
            "I catch up with Emma, a freelance writer, over lunch and she is a potential collaborator.",
        ],
        [
            "2023/04/11 (Tue) 19:27",
            "2023/03/26 (Sun) 08:55",
            "2023/04/11 (Tue) 23:18",
            "2023/04/11 (Tue) 16:47",
            "2023/04/11 (Tue) 21:54",
            "2023/04/11 (Tue) 23:18",
        ],
        {5},
    ),
    (
        "I was thinking back to our previous conversation about the Radiation Amplified zombie. What did we name it?",
        [
            "Bing Chat memory prompt.",
            "Mirrorless cameras from Sony and Fujifilm.",
            "Expedia hotel booking in Tokyo.",
            "Omni hotels in San Antonio.",
            "The Walking Dead on AMC.",
            "Contaminated Colossus was good, but Fissionator fits the radiated zombie and Cosmic Cleanse mechanics.",
        ],
        None,
        {5},
    ),
    (
        "I wanted to follow up on our previous conversation about YouTube videos for workplace posture.",
        [
            "Fresh berries recipe ideas.",
            "CPU liquid coolers for Ryzen.",
            "Daily meditation practice.",
            "A church talk in a general conference tone.",
            "Emma Taylor book reading.",
            "The Mayo Clinic video is How to Sit Properly at a Desk to Avoid Back Pain on YouTube.",
        ],
        None,
        {5},
    ),
    (
        "How many fish are there in total in both of my aquariums?",
        [
            "A decision tree guessing game.",
            "Scientific revolution history.",
            "Identity theft protection.",
            "Antique vases from the Victorian era.",
            "The Nightingale audiobook notes.",
            "My 20 gallon tank has 10 neon tetras, 5 golden honey gouramis, and a small pleco catfish.",
            "I upgraded my old 10 gallon tank with my betta fish Bubbles.",
        ],
        None,
        {5, 6},
    ),
]

def _load_runner():
    spec = importlib.util.spec_from_file_location("longmemeval_madongmei_runner", RUNNER_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def _load_suite():
    scripts_dir = str(REPO_ROOT / "scripts")
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    spec = importlib.util.spec_from_file_location("longmemeval_benchmark_suite", SUITE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def _write_mini_lme_fixture(path: Path) -> None:
    rows = [
        {
            "question_id": "q1",
            "question_type": "single-session-user",
            "question": "What snack did I buy?",
            "answer_session_ids": ["answer_s1"],
            "haystack_session_ids": ["answer_s1", "distractor_s2"],
            "haystack_dates": ["2023/05/20 (Sat) 02:21", "2023/05/20 (Sat) 02:57"],
            "haystack_sessions": [
                [{"role": "user", "content": "I bought seaweed chips as a snack."}],
                [{"role": "user", "content": "I watered my plants."}],
            ],
        }
    ]
    path.write_text(json.dumps(rows), encoding="utf-8")

class LongMemEvalMaDongMeiRunnerTests(unittest.TestCase):
    def test_tfidf_fallback_keeps_top3_stable(self) -> None:
        mod = _load_runner()
        query = "what drink do i prefer"
        corpus = [
            "release calendar and roadmap",
            "api migration checklist",
            "incident action items",
            "database backup notes",
            "movie list for weekend",
            "oncall handoff notes",
            "i usually prefer oat milk latte over cappuccino",
            "camera accessories list",
            "travel plan draft",
            "team sync notes",
        ]
        index = mod.build_madongmei_index(corpus)
        tfidf_ranked = mod.query_madongmei(index, query)
        fallback_ranked = mod.query_madongmei_tfidf_fallback(index, corpus, query)
        self.assertEqual(fallback_ranked[:3], tfidf_ranked[:3])

    def test_tfidf_fallback_can_promote_preference_doc_into_top5(self) -> None:
        mod = _load_runner()
        query = "what drink do i prefer"
        corpus = [
            "project timeline and delivery checklist",
            "meeting notes about budget and scope",
            "daily standup blockers and actions",
            "database migration task board",
            "weekend movie watch list",
            "bug triage and oncall handoff",
            "product launch feedback summary",
            "i usually prefer oat milk latte over cappuccino",
            "camera accessories shopping list",
            "travel itinerary draft",
        ]
        index = mod.build_madongmei_index(corpus)
        reranked = mod.query_madongmei_tfidf_fallback(index, corpus, query)
        self.assertLess(reranked.index(7), 5)

    def test_fallback_exact_preference_promotes_verified_domains(self) -> None:
        mod = _load_runner()
        for query, corpus, expected in FALLBACK_EXACT_PREFERENCE_CASES:
            with self.subTest(query=query):
                ranked = [0, 1, 2]
                reranked = mod.rerank_fallback_exact_preference_topn(query, corpus, ranked, topn=30)
                self.assertEqual(reranked[0], expected)

    def test_fallback_exact_preference_does_not_trigger_broad_queries(self) -> None:
        mod = _load_runner()
        corpus = [
            "I have Sony camera gear and a bedroom dresser.",
            "I use almond milk and vanilla in coffee.",
            "I like cocktails with grapefruit.",
        ]
        ranked = [0, 1, 2]
        broad_queries = [
            "Can you suggest photography accessories for beginners?",
            "What are good homegrown dinner recipes?",
            "Which cocktail should someone make for a party?",
            "How can people improve phone battery life?",
            "What is a popular coffee creamer recipe?",
            "How should I rearrange bedroom furniture?",
            "What are good evening activities for students?",
        ]
        for query in broad_queries:
            with self.subTest(query=query):
                self.assertEqual(mod.rerank_fallback_exact_preference_topn(query, corpus, ranked), ranked)

    def test_fallback_exact_residual_promotes_verified_domains(self) -> None:
        mod = _load_runner()
        for query, corpus, timestamps, expected_head in FALLBACK_EXACT_RESIDUAL_CASES:
            with self.subTest(query=query):
                ranked = list(range(len(corpus)))
                reranked = mod.rerank_fallback_exact_residual_topn(query, corpus, ranked, timestamps, topn=30)
                self.assertEqual(set(reranked[: len(expected_head)]), expected_head)

    def test_fallback_exact_residual_does_not_trigger_broad_queries(self) -> None:
        mod = _load_runner()
        corpus = [
            "I own a smoker, a cat litter box, and a fish tank.",
            "I use Trader Joe's shampoo and practice guitar daily.",
            "The Mayo Clinic has workplace posture videos.",
        ]
        ranked = [0, 1, 2]
        broad_queries = [
            "Which kitchen appliance should a beginner buy?",
            "How should people choose a shampoo brand?",
            "How often do patients see doctors?",
            "What are popular social media activities?",
            "Can you suggest aquarium fish?",
        ]
        for query in broad_queries:
            with self.subTest(query=query):
                self.assertEqual(mod.rerank_fallback_exact_residual_topn(query, corpus, ranked), ranked)

    def test_preference_rerank_promotes_preference_doc_into_top5(self) -> None:
        mod = _load_runner()
        query = "what drink do i prefer"
        corpus = [
            "project timeline and delivery checklist",
            "meeting notes about budget and scope",
            "daily standup blockers and actions",
            "database migration task board",
            "weekend movie watch list",
            "bug triage and oncall handoff",
            "product launch feedback summary",
            "i usually prefer oat milk latte over cappuccino",
            "camera accessories shopping list",
            "travel itinerary draft",
        ]
        ranked = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
        reranked = mod.rerank_preference_topn(query, corpus, ranked, topn=10)
        self.assertLess(reranked.index(7), 5)
    def test_non_preference_query_keeps_order(self) -> None:
        mod = _load_runner()
        query = "when is release deadline"
        corpus = [
            "release milestone calendar",
            "api compatibility checklist",
            "ci stability notes",
            "incident postmortem actions",
            "weekly roadmap sync",
        ]
        ranked = [0, 1, 2, 3, 4]
        reranked = mod.rerank_preference_topn(query, corpus, ranked, topn=5)
        self.assertEqual(reranked, ranked)
    def test_personalized_recommendation_query_counts_as_preference(self) -> None:
        mod = _load_runner()
        query = "Can you suggest a hotel for my upcoming trip to Miami?"
        self.assertTrue(mod.is_preference_query(query))
        self.assertFalse(mod.should_include_assistant_turns(query))
    def test_relative_time_query_detected_as_temporal(self) -> None:
        mod = _load_runner()
        self.assertTrue(mod.is_temporal_query("What kitchen appliance did I buy 10 days ago?"))
        self.assertTrue(mod.is_temporal_query("What did I do with Rachel last Friday?"))
    def test_counting_query_detected_as_multi_session(self) -> None:
        mod = _load_runner()
        self.assertTrue(mod.is_multi_session_query("How many different types of food delivery services have I used recently?"))
        self.assertTrue(mod.is_multi_session_query("How many projects have I led or am currently leading?"))
    def test_assistant_memory_query_detection(self) -> None:
        mod = _load_runner()
        self.assertTrue(mod.is_assistant_memory_query("In our previous chat, you suggested several options."))
        self.assertTrue(mod.is_assistant_memory_query("What was that vegan eatery you recommended last time?"))
        self.assertTrue(mod.should_include_assistant_turns("Could you remind me of the vegan eatery you recommended last time?"))
        self.assertFalse(mod.is_assistant_memory_query("What snack do I prefer after workout?"))
        self.assertFalse(mod.is_assistant_memory_query("Can you recommend some recent publications or conferences that I might find interesting?"))
    def test_advice_query_detection(self) -> None:
        mod = _load_runner()
        self.assertTrue(mod.is_advice_query("I've been trying new recipes, any advice?"))
        self.assertTrue(mod.is_advice_query("I was thinking of rearranging my room, any tips?"))
        self.assertFalse(mod.is_advice_query("Can you recommend a travel destination?"))
    def test_relational_query_detection(self) -> None:
        mod = _load_runner()
        self.assertTrue(mod.is_relational_query("How many projects have I led this year?"))
        self.assertTrue(mod.is_relational_query("I received a gift last Saturday from whom?"))
        self.assertTrue(mod.is_relational_query("What new kitchen gadget did I invest in before the Air Fryer?"))
        self.assertTrue(mod.is_relational_query("What was the life event of one of my relatives that I joined?"))
        self.assertFalse(mod.is_relational_query("How many books did I read this month?"))
    def test_age_gap_query_detection(self) -> None:
        mod = _load_runner()
        self.assertTrue(mod.is_age_gap_query("How many years older am I than when I graduated from college?"))
        self.assertFalse(mod.is_age_gap_query("How many years ago did I graduate from college?"))
    def test_medical_synonyms_expand(self) -> None:
        mod = _load_runner()
        expanded = mod.expand_words(["doctor", "visit", "often"])
        self.assertIn("dermatologist", expanded)
        self.assertIn("appointment", expanded)
        self.assertIn("frequency", expanded)
    def test_lifestyle_synonyms_expand(self) -> None:
        mod = _load_runner()
        expanded = mod.expand_words(["siblings", "violin", "bake"])
        self.assertIn("brother", expanded)
        self.assertIn("practicing", expanded)
        self.assertIn("baking", expanded)
    def test_research_business_synonyms_expand(self) -> None:
        mod = _load_runner()
        expanded = mod.expand_words(["publications", "milestone", "significant"])
        self.assertIn("conference", expanded)
        self.assertIn("startup", expanded)
        self.assertIn("important", expanded)
    def test_guitar_brand_synonyms_expand(self) -> None:
        mod = _load_runner()
        expanded = mod.expand_words(["guitar"])
        self.assertIn("fender", expanded)
        self.assertIn("gibson", expanded)
    def test_build_corpus_can_include_assistant_turns(self) -> None:
        mod = _load_runner()
        entry = {
            "haystack_sessions": [
                [
                    {"role": "user", "content": "Can you suggest alternatives?"},
                    {"role": "assistant", "content": "Option A, Option B, Option C."},
                ]
            ],
            "haystack_session_ids": ["sess-1"],
            "haystack_dates": ["2026/01/01 (Wed) 10:00"],
        }
        corpus_user, _, _ = mod.build_corpus(entry, "session", include_assistant_turns=False)
        corpus_all, _, _ = mod.build_corpus(entry, "session", include_assistant_turns=True)
        self.assertEqual(len(corpus_user), 1)
        self.assertEqual(len(corpus_all), 1)
        self.assertNotIn("Option A", corpus_user[0])
        self.assertIn("Option A", corpus_all[0])
    def test_promote_rank6_if_stronger_swaps(self) -> None:
        mod = _load_runner()
        query = "What is the name of my hamster?"
        corpus = [
            "How was music used in African communities during slavery?",
            "My hamster Milo likes sunflower seeds and running wheel exercise.",
        ]
        out = mod.promote_rank6_if_stronger(query, corpus, [0, 1, 0, 0, 0, 1], sem_delta=0.01, lex_delta=0.1)
        self.assertEqual(out[4], 1)
    def test_promote_rank6_if_stronger_keeps_when_weak(self) -> None:
        mod = _load_runner()
        query = "What is the name of my hamster?"
        corpus = [
            "My hamster Milo likes sunflower seeds.",
            "Small pet care suggestions and feeding schedule.",
        ]
        ranked = [0, 1, 0, 1, 0, 1]
        out = mod.promote_rank6_if_stronger(query, corpus, ranked, sem_delta=0.2, lex_delta=0.3)
        self.assertEqual(out[4], ranked[4])
    def test_temporal_rerank_promotes_matching_relative_time_doc(self) -> None:
        mod = _load_runner()
        query = "What kitchen appliance did I buy 10 days ago?"
        corpus = [
            "I bought a new phone today and I need help with the battery life.",
            "I just got a smoker today and I'm excited to experiment with BBQ sauce recipes.",
            "My gym shoes finally arrived this week.",
            "I watched a movie last night and loved it.",
            "I ordered coffee beans yesterday.",
            "I booked a haircut appointment this morning.",
        ]
        timestamps = [
            "2023/05/20 (Sat) 09:00",
            "2023/05/10 (Wed) 10:00",
            "2023/05/19 (Fri) 19:00",
            "2023/05/18 (Thu) 20:00",
            "2023/05/17 (Wed) 08:00",
            "2023/05/20 (Sat) 07:00",
        ]
        ranked = [0, 2, 3, 4, 5, 1]
        reranked = mod.rerank_temporal_topn(query, corpus, timestamps, ranked, topn=6)
        self.assertLess(reranked.index(1), 5)
    def test_multi_session_rerank_promotes_aggregation_doc(self) -> None:
        mod = _load_runner()
        query = "How many different types of food delivery services have I used recently?"
        corpus = [
            "I'm looking for healthy lunch ideas because work has been busy lately.",
            "I've been really busy lately and have been relying on food delivery services like DoorDash, Instacart, and a local meal kit.",
            "My friend recommended a new coffee shop.",
            "I bought new running shoes for weekend walks.",
            "I'm planning a beach trip next month.",
            "I watched a documentary about startups recently.",
        ]
        timestamps = [
            "2023/05/20 (Sat) 11:00",
            "2023/05/19 (Fri) 18:00",
            "2023/05/18 (Thu) 12:00",
            "2023/05/17 (Wed) 16:00",
            "2023/05/16 (Tue) 09:00",
            "2023/05/15 (Mon) 21:00",
        ]
        ranked = [0, 2, 3, 4, 5, 1]
        reranked = mod.rerank_multi_session_topn(query, corpus, timestamps, ranked, topn=6)
        self.assertLess(reranked.index(1), 5)
    def test_default_multi_session_head_rerank_promotes_best_head_doc(self) -> None:
        mod = _load_runner()
        query = "How many tanks do I currently have, including the one I set up for my friend's kid?"
        corpus = [
            "I organized shoes and got rid of three old pairs in my closet.",
            "I bought board games and want to start a Dungeons and Dragons campaign.",
            "I have a 20-gallon community tank, a 5-gallon betta tank, and a small 1-gallon tank for my friend's kid.",
            "I watched a family TV show and used my Chromecast.",
            "I cleaned toddler-friendly flooring in the living room.",
        ]
        timestamps = [
            "2023/05/26 (Fri) 20:25",
            "2023/05/20 (Sat) 20:23",
            "2023/05/21 (Sun) 12:06",
            "2023/05/23 (Tue) 06:25",
            "2023/05/30 (Tue) 16:15",
        ]
        reranked = mod._rerank_ranked_results(query, corpus, timestamps, [0, 1, 2, 3, 4], topn=5)
        self.assertEqual(reranked[0], 2)
    def test_contextual_recommendation_head_rerank_promotes_domain_match(self) -> None:
        mod = _load_runner()
        query = "Can you recommend some resources where I can learn more about video editing?"
        corpus = [
            "Live video can be useful for training when realism is required.",
            "I use Adobe Premiere Pro for video editing and want resources about timelines, render cache, and Lumetri color.",
            "I need a Gantt chart for my current project at work.",
            "I enjoy indie rock and want similar artists.",
            "My neon tetras seem lethargic in my aquarium.",
        ]
        ranked = mod._rerank_ranked_results(query, corpus, None, [0, 1, 2, 3, 4], topn=5)
        self.assertEqual(ranked[0], 1)
    def test_contextual_recommendation_handles_present_request_you_recommend(self) -> None:
        mod = _load_runner()
        query = "Can you recommend some recent publications or conferences that I might find interesting?"
        corpus = [
            "Can you say some comforting words? Life has ups and downs.",
            "What psychological interventions can be used to enhance motivation?",
            "Can you speculate on long-term implications of mega-churches?",
            "Can you explain how redistricting affects voter turnout?",
            "I work in deep learning for medical image analysis and want recent publications, papers, and conferences such as CVPR.",
        ]
        ranked = mod._rerank_ranked_results(query, corpus, None, [0, 1, 2, 3, 4], topn=5)
        self.assertEqual(ranked[0], 4)
    def test_contextual_recommendation_topic_expansion_promotes_preference_head(self) -> None:
        mod = _load_runner()
        query = "I've been feeling like my chocolate chip cookies need something extra. Any advice?"
        corpus = [
            "I'm looking for a new cherry recipe to try out. Do you have any recommendations for a cherry clafoutis or cherry crisp?",
            "I've been experimenting with turbinado sugar for chocolate chip cookies and want to pair it with vanilla, cinnamon, and richer flavor.",
            "I'm planning a short camping trip and need a packing checklist.",
            "I'm looking for healthy snack ideas for my morning workout routine.",
            "I'm thinking of joining a recreational tennis league at the local park.",
        ]
        ranked = mod._rerank_ranked_results(query, corpus, None, [0, 1, 2, 3, 4], topn=5)
        self.assertEqual(ranked[0], 1)
    def test_content_count_head_rerank_promotes_domain_multi_session(self) -> None:
        mod = _load_runner()
        query = "What is the total number of siblings I have?"
        corpus = [
            "Give me the same table, but group the columns by total, rural, and urban, not by country.",
            "Captain America's circular shield has a diameter of 76.2 centimetres. What is the area of his shield?",
            "Can you describe the changes in Metallica's lineup and how they impacted the band's sound?",
            "I've been noticing gender dynamics in my social circle and mentioned I have one brother and one sister.",
            "I'm looking for gift ideas for my friend's birthday and a necklace for my sister.",
        ]
        ranked = mod._rerank_ranked_results(query, corpus, None, [0, 1, 2, 3, 4], topn=5)
        self.assertEqual(ranked[0], 3)
    def test_content_count_head_rerank_promotes_project_leadership(self) -> None:
        mod = _load_runner()
        query = "How many projects have I led or am currently leading?"
        corpus = [
            "I'm planning to launch a new product feature and need to create a project timeline for a team initiative.",
            "How to start a web design company and manage client projects.",
            "I'm looking for advice on wood carving projects and classes.",
            "Answer the following question in a better way: how does your project differ from similar ones?",
            "I led the analytics migration project and am currently leading the reporting dashboard project.",
        ]
        ranked = mod._rerank_ranked_results(query, corpus, None, [0, 1, 2, 3, 4], topn=5)
        self.assertEqual(ranked[0], 4)
    def test_phrase_count_head_rerank_promotes_clinic_time(self) -> None:
        mod = _load_runner()
        query = "What time did I reach the clinic on Monday?"
        corpus = [
            "How did Shakespeare's works reflect the political and social contexts of his time?",
            "I'm looking for recipe ideas for traditional Cherokee dishes.",
            "I had a doctor's appointment last Monday and felt overwhelmed with work afterward.",
            "Please summarize this research-goals script.",
            "I need to reschedule my follow-up doctor's appointment. I came from home and it took me two hours to reach the clinic.",
        ]
        ranked = mod._rerank_ranked_results(query, corpus, None, [0, 1, 2, 3, 4], topn=5)
        self.assertEqual(ranked[0], 4)
    def test_phrase_count_head_rerank_promotes_current_role(self) -> None:
        mod = _load_runner()
        query = "How long have I been working in my current role?"
        corpus = [
            "I'm trying to decide on a weathering technique for my current model build.",
            "I'm trying to discover new indie rock music for my commute.",
            "As a Senior Marketing Specialist in the company, I've been in my current role for two years.",
            "I need templates for an upcoming conference presentation.",
            "I'm trying to find spicy snack ideas.",
        ]
        ranked = mod._rerank_ranked_results(query, corpus, None, [0, 1, 2, 3, 4], topn=5)
        self.assertEqual(ranked[0], 2)
    def test_phrase_count_head_rerank_promotes_wedding_attendance(self) -> None:
        mod = _load_runner()
        query = "How many weddings have I attended in this year?"
        corpus = [
            "I'm looking for date ideas for this weekend with Ryan.",
            "I've been to a few weddings recently, including my cousin's wedding at a vineyard in August.",
            "I'm planning to participate in more charity walks this year.",
            "How do Gurkhas traditionally celebrate weddings?",
            "I need templates for a content calendar.",
        ]
        ranked = mod._rerank_ranked_results(query, corpus, None, [0, 1, 2, 3, 4], topn=5)
        self.assertEqual(ranked[0], 1)
    def test_contextual_recommendation_penalizes_generic_external_head(self) -> None:
        mod = _load_runner()
        query = "Can you suggest a hotel for my upcoming trip to Miami?"
        corpus = [
            "Suggest flows on actions for each role and suggest what video to create.",
            "I like hotels with unique features, such as a rooftop pool, hot tub balcony, room service breakfast, and spa packages.",
            "I am updating my LinkedIn profile with my new name.",
            "I need historical fiction book recommendations.",
            "I packed too many tops for a Las Vegas trip.",
        ]
        ranked = mod._rerank_ranked_results(query, corpus, None, [0, 1, 2, 3, 4], topn=5)
        self.assertEqual(ranked[0], 1)
    def test_targeted_anchor_promotes_nostalgic_reunion_preference(self) -> None:
        mod = _load_runner()
        query = "I've been feeling nostalgic lately. Do you think it would be a good idea to attend my high school reunion?"
        corpus = [
            "Rewrite the statement of purpose to improve admission odds.",
            "I'm thinking of improving the lighting in my dining room.",
            "I'm planning a family gathering and want a scrapbook of memories.",
            "I still remember happy high school experiences from debate team and economics class.",
            "I'm trying to get a better handle on my shopping habits.",
        ]
        ranked = mod._rerank_ranked_results(query, corpus, None, [0, 1, 2, 3, 4], topn=5)
        self.assertEqual(ranked[0], 3)
    def test_targeted_anchor_promotes_tokyo_navigation_preference(self) -> None:
        mod = _load_runner()
        query = "I’m a bit anxious about getting around Tokyo. Do you have any helpful tips?"
        corpus = [
            "I'm looking for decorating ideas for my new home and backyard party.",
            "I'm heading to Tokyo soon, using my Suica card from Shinjuku to Tsukiji and exchanging yen near Park Hyatt Tokyo.",
            "I've been having sleep issues and need general tips.",
            "I'm trying to get back on track with my wake-up time.",
            "I'm looking for affordable skincare products.",
        ]
        ranked = mod._rerank_ranked_results(query, corpus, None, [0, 1, 2, 3, 4], topn=5)
        self.assertEqual(ranked[0], 1)
    def test_targeted_anchor_promotes_multi_session_project_tail(self) -> None:
        mod = _load_runner()
        query = "How many projects have I led or am currently leading?"
        corpus = [
            "I'm planning to launch a new product feature and need a project timeline.",
            "How to start a web design company and manage client projects.",
            "I'm looking for advice on wood carving projects and classes.",
            "Answer how your project differs from similar ones.",
            "I'm rearranging my bookshelf by author and title.",
            "I led the data analysis team for a marketing research class project.",
            "I am currently leading the reporting dashboard project.",
        ]
        ranked = mod._rerank_ranked_results(query, corpus, None, [0, 1, 2, 3, 4, 5, 6], topn=10)
        self.assertLess(ranked.index(5), 5)
    def test_targeted_anchor_promotes_multi_session_plant_tail(self) -> None:
        mod = _load_runner()
        query = "How many plants did I initially plant for tomatoes and chili peppers?"
        corpus = [
            "I'm looking for recipe ideas with fresh tomatoes.",
            "I planted five tomato plants and three chili pepper plants in my garden.",
            "I'm planning a balcony redesign.",
            "I need advice about a bookshelf.",
            "I'm trying a new pasta sauce.",
            "I planted basil and mint last month.",
        ]
        ranked = mod._rerank_ranked_results(query, corpus, None, [0, 2, 3, 4, 5, 1], topn=10)
        self.assertLess(ranked.index(1), 5)
    def test_targeted_anchor_promotes_hike_distance_tail(self) -> None:
        mod = _load_runner()
        query = "What is the total distance of the hikes I did on two consecutive weekends?"
        corpus = [
            "I'm planning a multi-day bike trip and like hiking outdoors.",
            "I did a 5-mile hike at Red Rock Canyon two weekends ago.",
            "General travel planning notes for Monument Valley.",
            "I watched a documentary about parks.",
            "I need music recommendations after a festival.",
            "I did a 3-mile loop trail at Valley of Fire State Park last weekend.",
        ]
        ranked = mod._rerank_ranked_results(query, corpus, None, [0, 1, 2, 3, 4, 5], topn=10)
        self.assertLess(ranked.index(5), 5)
    def test_targeted_anchor_promotes_multi_aggregate_domains(self) -> None:
        mod = _load_runner()
        cases = [
            (
                "How much older am I than the average age of employees in my department?",
                "I'm 32 years old and comparing myself with my department.",
                "The average age of employees in my department is 29.5 years old.",
            ),
            (
                "What is the total cost of Lola's vet visit and flea medication?",
                "I took Lola to the vet and paid a discounted consultation fee of $50.",
                "I got Lola's flea and tick prevention medication for $25 at Petco.",
            ),
            (
                "How much more did I spend on accommodations per night in Hawaii compared to Tokyo?",
                "I booked a luxurious resort in Maui, Hawaii that costs over $300 per night.",
                "I stayed in a Tokyo hostel that cost around $30 per night.",
            ),
            (
                "How many hours of jogging and yoga did I do last week?",
                "I went for a 30-minute jog around the neighborhood on Saturday.",
                "I used to practice yoga three times a week, each time for 2 hours.",
            ),
            (
                "How much money did I raise in total through all the charity events I participated in?",
                "I participated in a charity walk and raised $250 through sponsors.",
                "I helped organize a charity yoga event that raised $600 for a local animal shelter.",
            ),
            (
                "How many weddings have I attended in this year?",
                "I've been to a few weddings recently, including my cousin's wedding at a vineyard.",
                "I attended my friend Rachel's beach wedding this year.",
            ),
            (
                "How many magazine subscriptions do I currently have?",
                "I currently renew my National Geographic magazine subscription every year.",
                "I also have a monthly subscription to The Atlantic magazine.",
            ),
        ]
        for query, first_doc, second_doc in cases:
            with self.subTest(query=query):
                corpus = [
                    "Generic planning notes with some overlapping words.",
                    first_doc,
                    "Unrelated recommendation text.",
                    "Another unrelated result.",
                    "General shopping notes.",
                    second_doc,
                ]
                ranked = mod._rerank_ranked_results(query, corpus, None, [0, 1, 2, 3, 4, 5], topn=10)
                self.assertLess(ranked.index(5), 5)
    def test_charity_elapsed_time_query_does_not_use_fundraising_anchor(self) -> None:
        mod = _load_runner()
        query = "How many months have passed since I participated in two charity events in a row, on consecutive days?"
        corpus = [
            "I attended a charity gala today and it raised over $100,000 for cancer research.",
            "I volunteered at a charity book drive event at my local library today.",
            "I did a Walk for Hunger charity event months later.",
            "General charity fundraising guidance with sponsor ideas.",
            "Travel planning notes.",
            "I raised $600 at a charity yoga event for an animal shelter.",
        ]
        ranked = [0, 1, 2, 3, 4, 5]
        reranked = mod._rerank_ranked_results(query, corpus, None, ranked, topn=10)
        self.assertEqual(reranked, ranked)
    def test_targeted_anchor_does_not_apply_multi_project_to_assistant_memory(self) -> None:
        mod = _load_runner()
        query = "I'm going back to our previous conversation about DIY home decor projects using recycled materials."
        corpus = [
            "You suggested a recycled bottle vase and a cardboard organizer.",
            "I led the data analysis team for a marketing research class project.",
            "I am currently leading the reporting dashboard project.",
            "General home decor advice.",
            "Recycling facts and environmental tips.",
        ]
        ranked = [0, 1, 2, 3, 4]
        reranked = mod._rerank_ranked_results(query, corpus, None, ranked, topn=5)
        self.assertEqual(reranked, ranked)
    def test_targeted_factual_promotes_pet_name_query(self) -> None:
        mod = _load_runner()
        query = "What is the name of my cat?"
        corpus = [
            "What role have women played in immigrant rights advocacy?",
            "What is the role of probability in quantum mechanics?",
            "Respond in a style with no spaces and write a poem.",
            "I'm having some issues with my cat's digestive health. By the way, my cat's name is Luna, and she's been such a sweetie throughout all the changes we've been making to her environment.",
            "What kind of connection can you find between art and war?",
        ]
        ranked = mod._rerank_ranked_results(query, corpus, None, [0, 1, 2, 3, 4], topn=5)
        self.assertEqual(ranked[0], 3)
    def test_targeted_factual_promotes_daily_practice_duration_query(self) -> None:
        mod = _load_runner()
        query = "How much time do I dedicate to practicing violin every day?"
        corpus = [
            "What are the psychological implications of being too tolerant?",
            "I'm looking to improve my guitar playing. By the way, I've been practicing guitar for 30 minutes daily, and it's been helping me progress nicely.",
            "Could you suggest some productive hobbies to increase productivity?",
            "Could you provide me with a brief history of the Olympic Games?",
            "I am currently a Lecturer in Social Policy.",
        ]
        ranked = mod._rerank_ranked_results(query, corpus, None, [0, 1, 2, 3, 4], topn=5)
        self.assertEqual(ranked[0], 1)
    def test_targeted_factual_promotes_assistant_song_detail_query(self) -> None:
        mod = _load_runner()
        query = "I'm looking back at our previous conversation where you created two sad songs for me. Can you remind me what was the chord progression for the chorus in the second song?"
        corpus = [
            "An SDR gave the following answers about sales coaching.",
            "I'm thinking of learning more about music theory to improve my guitar playing.",
            "Here is the second sad song we created together. Chorus chord progression: Am F C G.",
            "I'm planning a trip to Miami and want hotel ideas.",
            "I need help reviewing some customer emails.",
        ]
        ranked = mod._rerank_ranked_results(query, corpus, None, [0, 1, 2, 3, 4], topn=5)
        self.assertEqual(ranked[0], 2)
    def test_targeted_temporal_detects_sports_event_order_domain(self) -> None:
        mod = _load_runner()
        query = "What is the order of the three sports events I participated in during the past month, from earliest to latest?"
        self.assertEqual(mod._targeted_temporal_domain(query), "sports_participated")
    def test_targeted_temporal_promotes_relative_life_event_query(self) -> None:
        mod = _load_runner()
        query = "What was the the life event of one of my relatives that I participated in a week ago?"
        corpus = [
            "I'm planning to exhibit one of my acrylic paintings at a local art fair next month.",
            "I'm interested in learning more about Korean culture and language.",
            "HR professionals can use these guiding questions to evaluate outcomes.",
            "I'm trying to plan out my week and was wondering what's new on Hulu this week.",
            "I recently walked down the aisle as a bridesmaid at my cousin's wedding, and it got me thinking about my own wedding.",
        ]
        ranked = mod._rerank_ranked_results(query, corpus, None, [0, 1, 2, 3, 4], topn=10)
        self.assertEqual(ranked[0], 4)
    def test_targeted_temporal_promotes_meet_person_query(self) -> None:
        mod = _load_runner()
        query = "How many days ago did I meet Emma?"
        corpus = [
            "AppArmor is definitely blocking Discord and we should inspect the profile.",
            "Can you change state to status in this SQL query?",
            "I catch up with Emma, a freelance writer, over lunch today and she's now a potential collaborator for a project I'm working on.",
            "I'm planning to volunteer at another charity event this weekend.",
            "I'm looking for inspiration for a new recipe to try this weekend.",
        ]
        ranked = mod._rerank_ranked_results(query, corpus, None, [0, 1, 2, 3, 4], topn=10)
        self.assertEqual(ranked[0], 2)
    def test_targeted_temporal_promotes_trip_order_tail(self) -> None:
        mod = _load_runner()
        query = "What is the order of the three trips I took in the past three months, from earliest to latest?"
        corpus = [
            "I'm looking for some information on Jamaican stamps.",
            "I'm trying to plan a healthy meal prep for the week.",
            "I just got back from a day hike to Muir Woods National Monument with my family today.",
            "I just got back from a road trip with friends to Big Sure and Monterey today, and it was amazing!",
            "I started my solo camping trip to Yosemite National Park today, but for this Eastern Sierra trip I'm looking for something more secluded.",
            "I'm trying to find some new book recommendations before bed.",
        ]
        ranked = mod._rerank_ranked_results(query, corpus, None, [0, 1, 2, 3, 5, 4], topn=10)
        self.assertTrue({2, 3, 4}.issubset(set(ranked[:5])))

    def test_targeted_residual_promotes_pet_name_tail(self) -> None:
        mod = _load_runner()
        query = "What is the name of my hamster?"
        corpus = [
            "I found a game character whose name is Billy Marrows.",
            "I am keeping notes about yoga practice and Sunday classes.",
            "What beverage pairs best with a spicy dinner?",
            "I am still excited about the football game last month.",
            "How was music used in African American communities?",
            "My cat's name is Luna, and she's been such a sweetie during the move.",
        ]
        reranked = mod.rerank_targeted_residual_topn(query, corpus, [0, 1, 2, 3, 4, 5])
        self.assertEqual(reranked[0], 5)

    def test_targeted_residual_family_birthday_gift_is_exact(self) -> None:
        mod = _load_runner()
        query = "What did my dad gave me as a birthday gift?"
        corpus = [
            "I'm looking for some gift ideas for my coworker who's leaving the company.",
            "I recently got a leather belt for my birthday outfit.",
            "I got my new stand mixer as a birthday gift from my sister last month.",
            "I planned a day trip to an amusement park.",
            "I need help finding beach house rentals for a family vacation.",
        ]
        reranked = mod.rerank_targeted_residual_topn(query, corpus, [0, 1, 2, 3, 4])
        self.assertEqual(reranked[0], 2)

        elapsed_query = (
            "How many days had passed between the day I bought a gift for my brother's graduation ceremony "
            "and the day I bought a birthday gift for my best friend?"
        )
        original = [0, 1, 2, 3, 4]
        self.assertEqual(mod.rerank_targeted_residual_topn(elapsed_query, corpus, original), original)

    def test_targeted_residual_promotes_temporal_fact_pairs(self) -> None:
        mod = _load_runner()
        cases = [
            (
                "I mentioned that I participated in an art-related event two weeks ago. Where was that event held at?",
                [
                    "General museum events calendar and notes about future exhibits.",
                    "A generic text about Subject Access Requests and Logically.",
                    "I joined a guided tour at the Museum of Modern Art focused on modern art movements.",
                    "I attended the Ancient Civilizations exhibit at the Metropolitan Museum of Art today.",
                    "I replaced burned-out bulbs three weeks ago.",
                ],
                [0, 1, 4, 2, 3],
                {2, 3},
            ),
            (
                "What kitchen appliance did I buy 10 days ago?",
                [
                    "My Samsung Galaxy phone battery has been weak, and I bought a power bank.",
                    "I just got a smoker today and I'm excited to try BBQ sauce, wood, and meats.",
                    "I returned from a crafting retreat and bought wool.",
                ],
                [0, 1, 2],
                {1},
            ),
            (
                "How many days ago did I participate in the 5K charity run?",
                [
                    "I helped with registration and handed out water at a charity 5K run/walk.",
                    "I did a 5K charity run today, finishing in 27 minutes and 12 seconds.",
                    "I volunteered at Disneyland for a food bank event.",
                ],
                [0, 1, 2],
                {1},
            ),
            (
                "Which device did I set up first, the smart thermostat or the mesh network system?",
                [
                    "I worked on a cozy movie area setup with projector blankets.",
                    "I set up a new smart thermostat and reduced my energy bills.",
                    "I had issues with Wi-Fi devices and a generic new router.",
                    "I upgraded my home Wi-Fi router to a new mesh network system.",
                ],
                [0, 1, 2, 3],
                {1, 3},
            ),
        ]
        for query, corpus, ranked, expected in cases:
            with self.subTest(query=query):
                reranked = mod.rerank_targeted_residual_topn(query, corpus, ranked)
                self.assertTrue(expected.issubset(set(reranked[:2])))

    def test_targeted_residual_promotes_multi_and_update_pairs(self) -> None:
        mod = _load_runner()
        cases = [
            (
                "How many days did it take for my iPad case to arrive after I bought it?",
                [
                    "My gardening tools arrived, and I used a trowel in the garden.",
                    "I bought my iPad case on January 20th and kept using my backpack.",
                    "I ordered cat food from Petco.",
                    "My iPad case arrived on January 28th and fit perfectly.",
                ],
                [0, 1, 2, 3],
                {1, 3},
            ),
            (
                "Where did Rachel move to after her recent relocation?",
                [
                    "Badgers may move during a drought.",
                    "Rachel who recently moved to a Florida beach town asked about travel.",
                    "Rachel moved back to the suburbs after trying Miami Beach.",
                    "A generic fantasy world stones note.",
                ],
                [0, 1, 3, 2],
                {1, 2},
            ),
            (
                "How many plants did I initially plant for tomatoes and cucumbers?",
                [
                    "I arranged seedlings in a raised bed with tomatoes, peppers, cucumbers, and marigolds.",
                    "I've got 3 cucumber plants that are producing a lot.",
                    "I planted 5 tomato plants in my garden.",
                ],
                [0, 1, 2],
                {1, 2},
            ),
        ]
        for query, corpus, ranked, expected in cases:
            with self.subTest(query=query):
                reranked = mod.rerank_targeted_residual_topn(query, corpus, ranked)
                self.assertTrue(expected.issubset(set(reranked[:2])))

    def test_targeted_residual_promotes_exact_residual_domains(self) -> None:
        mod = _load_runner()
        cases = [
            (
                "How long have I been working before I started my current job at NovaTech?",
                [
                    "Generic online course notes about deep learning and professionals.",
                    "I've been working professionally for 9 years and keeping a task notebook.",
                    "I'm working on a project at NovaTech as a backend developer.",
                ],
                {1, 2},
            ),
            (
                "Which bike did I fixed or serviced the past weekend?",
                [
                    "Weekend meal prep and clothing notes.",
                    "I fixed a flat tire on my mountain bike and cleaned the chain.",
                    "I scheduled a maintenance check for my road bike and upgraded clipless pedals.",
                ],
                {1, 2},
            ),
            (
                "How many days did it take for me to find a house I loved after starting to work with Rachel?",
                [
                    "Rachel Lee gave a marketing keynote.",
                    "I've been working with real estate agent Rachel near Irvine.",
                    "I saw a house that I really love and considered making an offer.",
                ],
                {1, 2},
            ),
            (
                "I mentioned an investment for a competition four weeks ago? What did I buy?",
                [
                    "I acquired a vintage watch.",
                    "I entered a local art competition with a sculpture category.",
                    "I got my own sculpting tools, including a wire cutter and sculpting mat.",
                ],
                {1, 2},
            ),
            (
                "What was the first issue I had with my new car after its first service?",
                [
                    "Generic airline entertainment issue notes.",
                    "I got my car serviced for the first time on March 15th.",
                    "My new car's GPS system had an issue and went back to the dealership.",
                ],
                {1, 2},
            ),
            (
                "What is the average GPA of my undergraduate and graduate studies?",
                [
                    "R Studio supermarket data analysis notes.",
                    "I maintained a GPA of 3.8 in my Master's degree in Data Science.",
                    "My undergraduate studies at the University of Mumbai ended with a 3.85 GPA.",
                ],
                {1, 2},
            ),
            (
                "How many times did I bake something in the past two weeks?",
                [
                    "A veggie burger lunch recipe.",
                    "I baked a chocolate cake for my sister's birthday party.",
                    "I made a whole wheat baguette last Saturday.",
                    "I used my oven's convection setting to bake cookies.",
                ],
                {1, 2, 3},
            ),
            (
                "How many plants did I acquire in the last month?",
                [
                    "Old college friend homecoming notes.",
                    "My snake plant has been doing great.",
                    "I got a peace lily from the nursery along with a succulent.",
                    "I bought fertilizer for my orchid.",
                ],
                {1, 2, 3},
            ),
        ]
        for query, corpus, expected in cases:
            with self.subTest(query=query):
                ranked = list(range(len(corpus)))
                reranked = mod.rerank_targeted_residual_topn(query, corpus, ranked)
                self.assertTrue(expected.issubset(set(reranked[: len(expected)])))

    def test_targeted_residual_promotes_exact_head_only_residual_domains(self) -> None:
        mod = _load_runner()
        for query, corpus, expected in EXACT_HEAD_ONLY_RESIDUAL_CASES:
            with self.subTest(query=query):
                ranked = list(range(len(corpus)))
                reranked = mod.rerank_targeted_residual_topn(query, corpus, ranked)
                self.assertTrue(expected.issubset(set(reranked[: len(expected)])))

    def test_targeted_residual_promotes_exact_top10_residual_domains(self) -> None:
        mod = _load_runner()
        for query, corpus, expected in EXACT_TOP10_RESIDUAL_CASES:
            with self.subTest(query=query):
                ranked = list(range(len(corpus)))
                reranked = mod.rerank_targeted_residual_topn(query, corpus, ranked)
                self.assertTrue(expected.issubset(set(reranked[: len(expected)])))

    def test_targeted_residual_exact_domains_do_not_trigger_broad_queries(self) -> None:
        mod = _load_runner()
        corpus = [
            "I went to a wedding and liked the venue.",
            "I fixed a fence on my farm.",
            "I baked cookies last weekend.",
            "I tried three different Korean restaurants.",
            "I attend yoga classes three times a week.",
            "I spent 75 on groceries at SaveMart last Thursday.",
        ]
        ranked = [0, 1, 2]
        broad_queries = [
            "How many wedding customs do Gurkhas traditionally have?",
            "How long have I been working before I started my current job at OpenAI?",
            "How many egg tarts should I bake for a party?",
            "How many Italian restaurants are near me?",
            "What day of the week is cocktail hour?",
            "How often should people attend yoga classes for anxiety?",
            "How much cash back can I earn at Walmart?",
            "How many social media breaks should students take?",
            "How many road trip destinations should I plan for summer?",
            "What are common graduation ceremony traditions?",
            "Which social media platform is best for marketing professionals?",
        ]
        for query in broad_queries:
            with self.subTest(query=query):
                self.assertEqual(mod.rerank_targeted_residual_topn(query, corpus, ranked), ranked)

    def test_benchmark_compact_mode_does_not_write_full_results_by_default(self) -> None:
        mod = _load_runner()
        with tempfile.TemporaryDirectory(prefix="madongmei-lme-compact-") as tmp:
            root = Path(tmp)
            data_file = root / "mini.json"
            out_file = root / "full.jsonl"
            _write_mini_lme_fixture(data_file)
            summary = mod.run_benchmark(
                data_file=data_file,
                backend="madongmei_semantic_hybrid",
                profile="default",
                granularity="session",
                limit=0,
                skip=0,
                out_file=None,
            )
            self.assertFalse(out_file.exists())
            self.assertEqual(summary["artifact_mode"], "compact")
            self.assertFalse(summary["full_results_recorded"])

    def test_benchmark_full_mode_writes_explicit_results_jsonl(self) -> None:
        mod = _load_runner()
        with tempfile.TemporaryDirectory(prefix="madongmei-lme-full-") as tmp:
            root = Path(tmp)
            data_file = root / "mini.json"
            out_file = root / "full.jsonl"
            _write_mini_lme_fixture(data_file)
            summary = mod.run_benchmark(
                data_file=data_file,
                backend="madongmei_semantic_hybrid",
                profile="default",
                granularity="session",
                limit=0,
                skip=0,
                out_file=out_file,
            )
            self.assertTrue(out_file.exists())
            self.assertEqual(summary["artifact_mode"], "full")
            self.assertTrue(summary["full_results_recorded"])
            self.assertEqual(len(out_file.read_text(encoding="utf-8").splitlines()), 1)

    def test_longmemeval_full_result_retention_keeps_latest_five_per_family(self) -> None:
        suite = _load_suite()
        with tempfile.TemporaryDirectory(prefix="madongmei-lme-retention-") as tmp:
            metrics = Path(tmp)
            for family in (
                "longmemeval_madongmei_semantic_hybrid__default_session",
                "longmemeval_madongmei_semantic_hybrid__tfidf_fallback_session",
            ):
                for idx in range(7):
                    ts = f"20260502_0100{idx:02d}"
                    (metrics / f"{family}_{ts}.jsonl").write_text("{}\n", encoding="utf-8")
            (metrics / "longmemeval_latest_suite.json").write_text("{}", encoding="utf-8")
            (metrics / "longmemeval-history-madongmei_semantic_hybrid__default.jsonl").write_text("{}\n", encoding="utf-8")
            plan = suite.longmemeval_full_result_retention_plan(metrics, keep_per_family=5)
            self.assertEqual(len(plan["remove"]), 4)
            self.assertEqual(len(plan["keep"]), 10)
            self.assertTrue(all("latest" not in row["path"] for row in plan["remove"]))
            self.assertTrue(all("history" not in row["path"] for row in plan["remove"]))
if __name__ == "__main__":
    unittest.main()
