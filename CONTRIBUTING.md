# Contributing

Prerequisites:
- [Precommit](https://pre-commit.com/). Run `pre-commit install` to install the hooks
- [jq](https://jqlang.org/download/)


Thank you so much for your interest in contributing!

The [example file](example.json) shows you how to structure your new author object.
The [author docs](authors/schema.html) is auto-generated based on the schema file. It can be used to see which fields are required and what each field is for.
The [schema json file](schema/author.schema.json) contains the canonical structure we use for validation.

It's important for us to fact check all data in this dataset. We do our best to ensure it's as accurate as possible.

## New data

Thanks for helping add to the dataset!

### Guidelines

Please answer truthfully for an author's about origin: whether it was fully AI generated, AI assisted or you wrote it yourself. We are happy to accept AI contributions if they are factually correct and objective (the same applies for hand written contributions).

Some authors will have controversies. In general, we avoid including this as we're focusing on their literary work. This is a grey area, so feel free to ask.

## Updating existing data

If you're changing an existing field's value (e.g. an author's image), we will consider carefully whether this improves our dataset. This is highly subjective.

## Schema changes

If a schema change would be a breaking change (e.g. adding or removing a required field), please create an issue first to discuss this with us.

When you make a schema change, please also update the [authors example JSON file](authors/example.json). You can use AI if you wish.
