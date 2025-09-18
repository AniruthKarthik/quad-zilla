# subjects_data.py - Study materials and resources for different subjects
import random

SUBJECT_RESOURCES = {
    "math": {
        "topics": [
            "algebra", "calculus", "geometry", "statistics", "trigonometry", 
            "linear algebra", "differential equations", "discrete math", 
            "probability", "number theory"
        ],
        "study_tips": [
            "Practice solving problems daily - math skills improve with consistent practice!",
            "Work through example problems step by step before attempting homework",
            "Don't just memorize formulas - understand the reasoning behind them",
            "Create a formula sheet with key equations and practice using them",
            "Form study groups to solve challenging problems together",
            "Use visual aids like graphs and geometric representations",
            "Break complex problems into smaller, manageable steps",
            "Review your mistakes and understand where you went wrong"
        ],
        "resources": [
            "Khan Academy has excellent math tutorials with practice problems",
            "Try Wolfram Alpha for step-by-step solutions and graphing",
            "PatrickJMT on YouTube has clear math explanations",
            "MIT OpenCourseWare offers free college-level math courses",
            "Desmos graphing calculator is great for visualizing functions"
        ],
        "common_problems": [
            "algebraic equations", "graphing functions", "derivatives", "integrals",
            "word problems", "geometric proofs", "statistical analysis"
        ]
    },
    
    "physics": {
        "topics": [
            "mechanics", "thermodynamics", "electromagnetism", "quantum physics", 
            "optics", "waves", "relativity", "nuclear physics", "astrophysics",
            "fluid dynamics", "solid state physics"
        ],
        "study_tips": [
            "Always draw diagrams and free body diagrams for physics problems",
            "Connect mathematical concepts to real-world physical phenomena",
            "Practice dimensional analysis to check your answers",
            "Understand the fundamental principles before memorizing equations",
            "Work through derivations to understand where formulas come from",
            "Use analogies to relate abstract concepts to familiar experiences",
            "Practice unit conversions and estimation problems",
            "Solve problems conceptually before plugging in numbers"
        ],
        "resources": [
            "Professor Walter Lewin's MIT lectures are legendary for physics",
            "PhET Interactive Simulations help visualize physics concepts",
            "The Feynman Lectures on Physics for deeper understanding",
            "Khan Academy Physics covers fundamental concepts well",
            "Hyperphysics website has comprehensive physics explanations"
        ],
        "common_problems": [
            "kinematics problems", "force and motion", "energy conservation",
            "wave interference", "electric circuits", "magnetic fields"
        ]
    },
    
    "chemistry": {
        "topics": [
            "organic chemistry", "inorganic chemistry", "physical chemistry", 
            "biochemistry", "analytical chemistry", "environmental chemistry",
            "medicinal chemistry", "polymer chemistry", "electrochemistry"
        ],
        "study_tips": [
            "Practice drawing molecular structures and reaction mechanisms",
            "Use flashcards for chemical reactions and element properties",
            "Understand periodic trends and how they affect chemical behavior",
            "Practice balancing chemical equations regularly",
            "Connect molecular structure to chemical properties and reactivity",
            "Memorize common functional groups and their properties",
            "Practice stoichiometry problems with different types of reactions",
            "Use molecular models to visualize 3D structures"
        ],
        "resources": [
            "Crash Course Chemistry provides excellent topic overviews",
            "ChemSketch or ChemDraw software for drawing structures",
            "PubChem database for comprehensive molecular information",
            "Khan Academy Chemistry covers fundamental concepts",
            "Organic Chemistry Tutor on YouTube for problem solving"
        ],
        "common_problems": [
            "balancing equations", "stoichiometry", "organic synthesis",
            "acid-base reactions", "electrochemistry", "thermodynamics"
        ]
    },
    
    "biology": {
        "topics": [
            "cell biology", "genetics", "ecology", "evolution", "anatomy",
            "physiology", "molecular biology", "microbiology", "botany",
            "zoology", "biochemistry", "neuroscience", "immunology"
        ],
        "study_tips": [
            "Create detailed concept maps to connect biological processes",
            "Use mnemonics for remembering complex terminology",
            "Study biological processes as step-by-step flowcharts",
            "Practice with diagrams and label important structures",
            "Relate biological concepts to everyday examples and experiences",
            "Use flashcards for terminology and classification systems",
            "Draw and redraw biological structures from memory",
            "Connect structure to function in biological systems"
        ],
        "resources": [
            "Campbell Biology textbook is comprehensive and well-regarded",
            "Crash Course Biology covers major topics with engaging videos",
            "BioNinja has excellent summary sheets and diagrams",
            "Khan Academy Biology offers structured learning paths",
            "NCBI resources for current research and genetic information"
        ],
        "common_problems": [
            "cell processes", "genetics problems", "evolutionary relationships",
            "ecosystem interactions", "human anatomy", "physiological processes"
        ]
    },
    
    "computer_science": {
        "topics": [
            "programming", "algorithms", "data structures", "software engineering",
            "databases", "computer networks", "cybersecurity", "artificial intelligence",
            "machine learning", "web development", "mobile development"
        ],
        "study_tips": [
            "Practice coding regularly - programming is a hands-on skill",
            "Work on projects to apply theoretical knowledge",
            "Understand algorithms and their time/space complexity",
            "Learn to debug code systematically",
            "Study data structures and when to use each one",
            "Practice problem-solving on coding platforms",
            "Read other people's code to learn different approaches",
            "Build a portfolio of projects to showcase your skills"
        ],
        "resources": [
            "LeetCode and HackerRank for coding practice",
            "GitHub for version control and project hosting",
            "Stack Overflow for programming questions and answers",
            "Coursera and edX for structured CS courses",
            "Documentation for programming languages and frameworks"
        ],
        "common_problems": [
            "algorithm implementation", "debugging", "system design",
            "database queries", "web development", "data analysis"
        ]
    },
    
    "english": {
        "topics": [
            "literature analysis", "creative writing", "grammar", "composition",
            "poetry", "rhetoric", "linguistics", "critical thinking",
            "research writing", "technical writing"
        ],
        "study_tips": [
            "Read actively - take notes and ask questions while reading",
            "Practice writing regularly to improve your skills",
            "Analyze literary techniques and their effects",
            "Expand your vocabulary through reading and word study",
            "Practice different types of writing (essays, stories, reports)",
            "Learn to cite sources properly for research papers",
            "Read your work aloud to catch errors and improve flow",
            "Study grammar rules and practice applying them"
        ],
        "resources": [
            "Purdue OWL for writing and citation guidance",
            "Grammarly for grammar and style checking",
            "SparkNotes for literature summaries and analysis",
            "Project Gutenberg for free classic literature",
            "Merriam-Webster dictionary and thesaurus"
        ],
        "common_problems": [
            "essay structure", "grammar and punctuation", "literary analysis",
            "research and citations", "creative writing", "reading comprehension"
        ]
    },
    
    "history": {
        "topics": [
            "world history", "american history", "ancient civilizations",
            "modern history", "political history", "social history",
            "economic history", "cultural history", "military history"
        ],
        "study_tips": [
            "Create timelines to understand chronological relationships",
            "Connect historical events to their causes and consequences",
            "Study primary sources to understand historical perspectives",
            "Use maps to understand geographical context of events",
            "Practice analyzing historical arguments and evidence",
            "Create comparison charts for similar events or periods",
            "Use mnemonics for remembering dates and sequences",
            "Relate historical events to contemporary issues"
        ],
        "resources": [
            "Khan Academy World History for comprehensive coverage",
            "Library of Congress for primary source documents",
            "BBC History website for articles and documentaries",
            "National Geographic History for visual learning",
            "Smithsonian's History Explorer for interactive content"
        ],
        "common_problems": [
            "memorizing dates and events", "analyzing primary sources",
            "writing historical essays", "understanding causation",
            "comparing different time periods", "interpreting historical data"
        ]
    }
}

# General study techniques that apply to all subjects
GENERAL_STUDY_TIPS = [
    "Use the Pomodoro Technique: Study for 25 minutes, then take a 5-minute break",
    "Create a dedicated study space free from distractions",
    "Use active recall - test yourself instead of just re-reading notes",
    "Space out your study sessions over time rather than cramming",
    "Teach concepts to someone else to reinforce your understanding",
    "Get adequate sleep - your brain consolidates memories during sleep",
    "Take regular breaks to maintain focus and prevent burnout",
    "Use multiple senses when learning (visual, auditory, kinesthetic)",
    "Practice retrieval by doing practice tests and quizzes",
    "Connect new information to what you already know"
]

# Motivational quotes for when students are struggling
MOTIVATIONAL_QUOTES = [
    "The expert in anything was once a beginner. Keep going!",
    "Success is not final, failure is not fatal: it is the courage to continue that counts.",
    "Every master was once a disaster. Practice makes progress!",
    "The only way to learn mathematics is to do mathematics.",
    "In learning you will teach, and in teaching you will learn.",
    "Education is not preparation for life; education is life itself.",
    "The beautiful thing about learning is that no one can take it away from you.",
    "Mistakes are proof that you are trying. Learn from them and keep going!"
]

def get_subject_info(subject):
    """Get comprehensive information about a specific subject."""
    subject = subject.lower()
    if subject in SUBJECT_RESOURCES:
        return SUBJECT_RESOURCES[subject]
    return None

def get_study_tip_for_subject(subject):
    """Get a random study tip for a specific subject."""
    subject = subject.lower()
    if subject in SUBJECT_RESOURCES and "study_tips" in SUBJECT_RESOURCES[subject]:
        return random.choice(SUBJECT_RESOURCES[subject]["study_tips"])
    return random.choice(GENERAL_STUDY_TIPS)

def get_resources_for_subject(subject):
    """Get resources for a specific subject."""
    subject = subject.lower()
    if subject in SUBJECT_RESOURCES and "resources" in SUBJECT_RESOURCES[subject]:
        return SUBJECT_RESOURCES[subject]["resources"]
    return []