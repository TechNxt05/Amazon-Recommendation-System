# train_finetune.py
# Fine-tune a small DistilBERT classifier for fake review detection using datasets + transformers Trainer.
import argparse
from datasets import load_dataset, Dataset
from transformers import AutoTokenizer, AutoModelForSequenceClassification, TrainingArguments, Trainer
import numpy as np
import pandas as pd
import os

def prepare_dataset(csv_path):
    df = pd.read_csv(csv_path)
    return Dataset.from_pandas(df)

def main(args):
    model_name = "distilbert-base-uncased"
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    train_ds = prepare_dataset(args.train)
    val_ds = prepare_dataset(args.val)

    def tokenize_fn(ex):
        return tokenizer(ex["text"], truncation=True, padding="max_length", max_length=128)

    train_ds = train_ds.map(tokenize_fn, batched=True)
    val_ds = val_ds.map(tokenize_fn, batched=True)
    train_ds.set_format(type='torch', columns=['input_ids','attention_mask','label'])
    val_ds.set_format(type='torch', columns=['input_ids','attention_mask','label'])

    model = AutoModelForSequenceClassification.from_pretrained(model_name, num_labels=2)

    training_args = TrainingArguments(
        output_dir=args.output,
        num_train_epochs=3,
        per_device_train_batch_size=16,
        per_device_eval_batch_size=32,
        evaluation_strategy="epoch",
        save_total_limit=2,
        logging_steps=10,
        load_best_model_at_end=True
    )

    trainer = Trainer(model=model, args=training_args, train_dataset=train_ds, eval_dataset=val_ds)
    trainer.train()
    trainer.save_model(args.output)
    print("Saved model to", args.output)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--train", required=True)
    parser.add_argument("--val", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    main(args)
