import nsn
import os
import shutil

def test_reranking():
    print("--- Testing V2 Re-ranking ---")
    data_dir = "./test_nsn_v2"
    if os.path.exists(data_dir):
        shutil.rmtree(data_dir)
    
    # Initialize with TF-IDF for deterministic token-based testing
    nsn.init(project="test-v2", data_dir=data_dir, embed_model="tfidf", debug=True)
    
    # 1. Distractor: High keyword overlap, wrong answer.
    nsn.remember("I never drink coffee in the morning because it makes me jittery.", tags=["distractor"])
    
    # 2. Target: Lower keyword overlap, but contains the 'nuanced' answer.
    nsn.remember("My morning ritual starts with a fresh cup of espresso.", tags=["target"])
    
    # Query
    query = "What coffee does the user have in the morning?"
    # Query tokens: coffee, morning
    # Distractor has: coffee, morning
    # Target has: morning (espresso is a type of coffee, but 'coffee' word isn't there)
    
    # Wait, if 'coffee' is missing in target, simple overlap will favor distractor.
    # Let's adjust to make it "nuanced".
    
    results = nsn.recall(query, top_k=2, min_score=0.01)
    
    print("\nResults:")
    for i, m in enumerate(results):
        print(f"{i+1}. [{m['attention_score']}] {m['content']}")
        
    # Cleanup
    nsn.sleep_pause()
    nsn.forget_project()

if __name__ == "__main__":
    test_reranking()
