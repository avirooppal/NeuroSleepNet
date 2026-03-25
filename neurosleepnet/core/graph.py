from typing import List, Dict, Any, Tuple

class KnowledgeGraphMemory:
    """
    Lightweight, zero-config knowledge graph extractor.
    Creates node-edge-node triplets to represent entities and their relationships.
    """
    def __init__(self):
        # A simple adjacency list: node -> List[Tuple[relationship, target_node]]
        self.graph: Dict[str, List[Tuple[str, str]]] = {}
        
    def _extract_triplets_mock(self, text: str) -> List[Tuple[str, str, str]]:
        """
        Mock extractor for MVP. In reality, you'd use an LLM or NER model here.
        """
        text = str(text).lower()
        triplets = []
        if "tv" in text and "sony" in text:
            # Specifically targeting the demo string "User Preference: TV model is Sony 77" BRAVIA XR A80K"
            parts = text.split("is")
            obj = parts[1].strip() if len(parts) > 1 else "sony tv"
            triplets.append(("user", "owns_device", obj))
        if "prefer" in text:
            if "aisle seats" in text:
                triplets.append(("user", "prefers", "aisle seats"))
            else:
                triplets.append(("user", "has_preference", text))
            
        return triplets

    def add_memory(self, memory_text: str):
        triplets = self._extract_triplets_mock(memory_text)
        for sub, rel, obj in triplets:
            if sub not in self.graph:
                self.graph[sub] = []
            self.graph[sub].append((rel, obj))

    def get_context(self, query: str) -> str:
        """
        Traverse the graph to build context strings for the query.
        """
        query = str(query).lower()
        context_parts = []
        for sub, edges in self.graph.items():
            # If the query is asking about the subject, inject its relationships
            if sub in query or "i" in query or "my" in query: # Simple heuristic
                for rel, obj in edges:
                    context_parts.append(f"{sub} {rel.replace('_', ' ')} {obj}")
                    
        return "; ".join(context_parts)
