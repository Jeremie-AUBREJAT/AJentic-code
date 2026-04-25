# AJentic-code
# 🧠 WP Code Analyzer Agent (Local LLM)

Agent IA local permettant d’analyser automatiquement un plugin WordPress (PHP + JavaScript) fichier par fichier via un LLM local (Oobabooga + Gemma 4 E4B Q4_K_M) et de générer une structure JSON exploitable.

---

## 🎯 Objectif

Ce projet permet :

- d’analyser un plugin WordPress complet  
- fichier par fichier (1 appel LLM par fichier)  
- d’extraire :
  - classes
  - fonctions
  - hooks WordPress
  - endpoints AJAX
  - logique métier
- de générer un JSON global structuré
- de générer une documentation HTML

---

## ⚙️ Fonctionnement

Pipeline :

1. Détection du type d’entrée (zip ou dossier)
2. Extraction dans workspace
3. Scan des fichiers du projet
4. Analyse fichier par fichier via LLM (1 appel = 1 fichier)
5. Fusion des résultats en Python
6. Génération :
   - `output/result.json`
   - documentation HTML

---

## 🧠 LLM utilisé

- Backend : Oobabooga API (llama.cpp)
- Modèle : Gemma 4 E4B Q4_K_M
- Contexte : 128K tokens
- Température : 0.2
- Mode : instruct

---

## 📦 Format de sortie par fichier

```json
{
  "language": "php|js|unknown",
  "classes": [],
  "functions": [],
  "hooks": [],
  "ajax": [],
  "logic": []
}