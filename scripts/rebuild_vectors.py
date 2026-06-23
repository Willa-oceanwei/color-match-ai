from datetime import datetime
from services.embedding_service import embed_image, upsert_embedding
from services.google_drive import resolve_local_image_path
from services.google_sheet import read_colorboard, update_embedding_status


def main() -> None:
    now = datetime.now().strftime("%Y/%m/%d %H:%M")
    df = read_colorboard()
    rebuilt = 0
    for row in df:
        image_path = resolve_local_image_path(row["ImagePath"])
        if not image_path.exists():
            print(f"skip missing image: {row['ID']} {image_path}")
            continue
        embedding = embed_image(image_path)
        upsert_embedding(row["Material"], {
            "id": row["ID"],
            "image_path": row["ImagePath"],
            "formula_id": row.get("FormulaID", ""),
            "recipe_status": row.get("RecipeStatus", ""),
        }, embedding, now)
        update_embedding_status(row["ID"], "Y", now)
        rebuilt += 1
    print(f"rebuilt vectors: {rebuilt}")


if __name__ == "__main__":
    main()
