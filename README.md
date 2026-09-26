# Datasets

<p align="center">
  <a href="https://epilogue-club.github.io/datasets/docs/authors/index.html">
    <img
      src="https://img.shields.io/badge/View%20docs-DCD7C7?style=for-the-badge&amp;logo=readthedocs&amp;logoColor=333333"
      alt="View author schema documentation"
    />
  </a>
</p>

Datasets is a crowd-sourced effort to build a high-quality, factually correct dataset of authors. While datasets exist for books, it's harder to find a rich dataset of book authors. It includes an author's:
- Name
- Biography (short summary)
    - We make it clear if this was AI generated or assisted
- Headshot image (e.g. for a picture picture)
- Social links

This will be used by [Epilogue's database](https://epilogue.club/). When users of other book discovery platforms (e.g. Goodreads) contribute data
back, that data ends up become proprietary data for that platform. We feel it's only fair that users contributions should be made open and public.

## Contributing

Thanks for your interest! See our [contributing guidelines](CONTRIBUTING.md).

There are 2 main types of contributions:
1. Adding new data to authors/authors.json
2. Making a schema change

We also highly welcome changes that make contributions easier for others.

## Versioning

There are two different assets we version separately:
1. Dataset
2. Schema

### Dataset

The author dataset is currently unversioned.  New data will not change the schema version. This may change going forward.

### Schema changes

The data schemas are versioned using semantic versioning. This means you can reliably depend on the structure. Here is some guidance we try to follow:

| Schema change | Recommended version bump |
|---|---:|
| Fix descriptions, titles, examples, or formatting only | None |
| Add an optional property | Minor |
| Add an enum value | Minor |
| Loosen a constraint, such as increasing `maxLength` | Minor |
| Add an optional property | Minor |
| Remove a property from `required` | Major |
| Add a required property | Major |
| Remove an existing property, especially with `additionalProperties: false` | Major |
| Remove an enum value | Major |
| Tighten types, patterns, formats, or length limits | Major |
| Change the meaning of an existing field | Major |
| Change the JSON Schema dialect or validation semantics | Major |

## License

This is licensed under [ODbL](https://opendatacommons.org/licenses/odbl/1-0/).
