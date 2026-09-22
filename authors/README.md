# Epilogue Author

- [1. Property `Epilogue Author > id`](#id)
- [2. Property `Epilogue Author > name`](#name)
- [3. Property `Epilogue Author > image`](#image)
  - [3.1. Property `Epilogue Author > image > url`](#image_url)
  - [3.2. Property `Epilogue Author > image > source_url`](#image_source_url)
  - [3.3. Property `Epilogue Author > image > license`](#image_license)
- [4. Property `Epilogue Author > about`](#about)
  - [4.1. Property `Epilogue Author > about > text`](#about_text)
  - [4.2. Property `Epilogue Author > about > license`](#about_license)
  - [4.3. Property `Epilogue Author > about > source_url`](#about_source_url)
  - [4.4. Property `Epilogue Author > about > origin`](#about_origin)
    - [4.4.1. Property `Epilogue Author > about > origin > type`](#about_origin_type)
- [5. Property `Epilogue Author > social_links`](#social_links)
  - [5.1. Property `Epilogue Author > social_links > additionalProperties`](#social_links_additionalProperties)

**Title:** Epilogue Author

|                           |             |
| ------------------------- | ----------- |
| **Type**                  | `object`    |
| **Required**              | No          |
| **Additional properties** | Not allowed |

**Description:** Schema for a public author record.

| Property                         | Pattern | Type   | Deprecated | Definition | Title/Description                                            |
| -------------------------------- | ------- | ------ | ---------- | ---------- | ------------------------------------------------------------ |
| + [id](#id )                     | No      | string | No         | -          | Stable unique identifier for the author.                     |
| + [name](#name )                 | No      | string | No         | -          | Public display name of the author.                           |
| + [image](#image )               | No      | object | No         | -          | Image and attribution metadata for the author.               |
| + [about](#about )               | No      | object | No         | -          | Attributed biographical information about the author.        |
| - [social_links](#social_links ) | No      | object | No         | -          | Public social or reference links associated with the author. |

## <a name="id"></a>1. Property `Epilogue Author > id`

|              |          |
| ------------ | -------- |
| **Type**     | `string` |
| **Required** | Yes      |

**Description:** Stable unique identifier for the author.

| Restrictions   |   |
| -------------- | - |
| **Min length** | 1 |

## <a name="name"></a>2. Property `Epilogue Author > name`

|              |          |
| ------------ | -------- |
| **Type**     | `string` |
| **Required** | Yes      |

**Description:** Public display name of the author.

| Restrictions   |   |
| -------------- | - |
| **Min length** | 1 |

## <a name="image"></a>3. Property `Epilogue Author > image`

|                           |             |
| ------------------------- | ----------- |
| **Type**                  | `object`    |
| **Required**              | Yes         |
| **Additional properties** | Not allowed |

**Description:** Image and attribution metadata for the author.

| Property                           | Pattern | Type   | Deprecated | Definition | Title/Description                          |
| ---------------------------------- | ------- | ------ | ---------- | ---------- | ------------------------------------------ |
| + [url](#image_url )               | No      | string | No         | -          | URL of the image used for the author.      |
| + [source_url](#image_source_url ) | No      | string | No         | -          | URL identifying the original image source. |
| + [license](#image_license )       | No      | string | No         | -          | License under which the image may be used. |

### <a name="image_url"></a>3.1. Property `Epilogue Author > image > url`

|              |          |
| ------------ | -------- |
| **Type**     | `string` |
| **Required** | Yes      |
| **Format**   | `uri`    |

**Description:** URL of the image used for the author.

| Restrictions                      |                                                                           |
| --------------------------------- | ------------------------------------------------------------------------- |
| **Must match regular expression** | ```^https?://``` [Test](https://regex101.com/?regex=%5Ehttps%3F%3A%2F%2F) |

### <a name="image_source_url"></a>3.2. Property `Epilogue Author > image > source_url`

|              |          |
| ------------ | -------- |
| **Type**     | `string` |
| **Required** | Yes      |
| **Format**   | `uri`    |

**Description:** URL identifying the original image source.

| Restrictions                      |                                                                           |
| --------------------------------- | ------------------------------------------------------------------------- |
| **Must match regular expression** | ```^https?://``` [Test](https://regex101.com/?regex=%5Ehttps%3F%3A%2F%2F) |

### <a name="image_license"></a>3.3. Property `Epilogue Author > image > license`

|              |          |
| ------------ | -------- |
| **Type**     | `string` |
| **Required** | Yes      |

**Description:** License under which the image may be used.

| Restrictions   |   |
| -------------- | - |
| **Min length** | 1 |

## <a name="about"></a>4. Property `Epilogue Author > about`

|                           |             |
| ------------------------- | ----------- |
| **Type**                  | `object`    |
| **Required**              | Yes         |
| **Additional properties** | Not allowed |

**Description:** Attributed biographical information about the author.

| Property                           | Pattern | Type   | Deprecated | Definition | Title/Description                                         |
| ---------------------------------- | ------- | ------ | ---------- | ---------- | --------------------------------------------------------- |
| + [text](#about_text )             | No      | string | No         | -          | Biographical text describing the author.                  |
| + [license](#about_license )       | No      | string | No         | -          | License under which the biographical text may be used.    |
| + [source_url](#about_source_url ) | No      | string | No         | -          | URL identifying the source of the biographical text.      |
| + [origin](#about_origin )         | No      | object | No         | -          | Information about how the biographical text was produced. |

### <a name="about_text"></a>4.1. Property `Epilogue Author > about > text`

|              |          |
| ------------ | -------- |
| **Type**     | `string` |
| **Required** | Yes      |

**Description:** Biographical text describing the author.

| Restrictions   |     |
| -------------- | --- |
| **Min length** | 1   |
| **Max length** | 512 |

### <a name="about_license"></a>4.2. Property `Epilogue Author > about > license`

|              |          |
| ------------ | -------- |
| **Type**     | `string` |
| **Required** | Yes      |

**Description:** License under which the biographical text may be used.

| Restrictions   |   |
| -------------- | - |
| **Min length** | 1 |

### <a name="about_source_url"></a>4.3. Property `Epilogue Author > about > source_url`

|              |          |
| ------------ | -------- |
| **Type**     | `string` |
| **Required** | Yes      |
| **Format**   | `uri`    |

**Description:** URL identifying the source of the biographical text.

| Restrictions                      |                                                                           |
| --------------------------------- | ------------------------------------------------------------------------- |
| **Must match regular expression** | ```^https?://``` [Test](https://regex101.com/?regex=%5Ehttps%3F%3A%2F%2F) |

### <a name="about_origin"></a>4.4. Property `Epilogue Author > about > origin`

|                           |             |
| ------------------------- | ----------- |
| **Type**                  | `object`    |
| **Required**              | Yes         |
| **Additional properties** | Not allowed |

**Description:** Information about how the biographical text was produced.

| Property                      | Pattern | Type             | Deprecated | Definition | Title/Description                                                             |
| ----------------------------- | ------- | ---------------- | ---------- | ---------- | ----------------------------------------------------------------------------- |
| + [type](#about_origin_type ) | No      | enum (of string) | No         | -          | Origin of the biographical text: human-written, AI-generated, or AI-assisted. |

#### <a name="about_origin_type"></a>4.4.1. Property `Epilogue Author > about > origin > type`

|              |                    |
| ------------ | ------------------ |
| **Type**     | `enum (of string)` |
| **Required** | Yes                |

**Description:** Origin of the biographical text: human-written, AI-generated, or AI-assisted.

Must be one of:
* "human"
* "ai"
* "ai_assisted"

## <a name="social_links"></a>5. Property `Epilogue Author > social_links`

|                           |                                                                                           |
| ------------------------- | ----------------------------------------------------------------------------------------- |
| **Type**                  | `object`                                                                                  |
| **Required**              | No                                                                                        |
| **Additional properties** | [Each additional property must conform to the schema](#social_links_additionalProperties) |

**Description:** Public social or reference links associated with the author.

| Property                                  | Pattern | Type   | Deprecated | Definition | Title/Description                                         |
| ----------------------------------------- | ------- | ------ | ---------- | ---------- | --------------------------------------------------------- |
| - [](#social_links_additionalProperties ) | No      | string | No         | -          | HTTPS URL for the associated social or reference profile. |

### <a name="social_links_additionalProperties"></a>5.1. Property `Epilogue Author > social_links > additionalProperties`

|              |          |
| ------------ | -------- |
| **Type**     | `string` |
| **Required** | No       |
| **Format**   | `uri`    |

**Description:** HTTPS URL for the associated social or reference profile.

| Restrictions                      |                                                                           |
| --------------------------------- | ------------------------------------------------------------------------- |
| **Must match regular expression** | ```^https?://``` [Test](https://regex101.com/?regex=%5Ehttps%3F%3A%2F%2F) |

----------------------------------------------------------------------------------------------------------------------------
Generated using [json-schema-for-humans](https://github.com/coveooss/json-schema-for-humans) on 2026-09-22 at 07:47:44 +0100
