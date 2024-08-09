### Telicent Model Rest Service

#### Overview

Telicent Security Labels provides a functionality to run given model as a rest service, the default behaviour is
aligned with the example Telicent Model. As long as user defined model implements logic to build security labels, it
will be made available as an endpoint under `localhost:8000/api/v1/ingest` where a data header can be posted and
API would respond with the generated security labels.

For further information and advanced use cases, please refer to [telicent-label-builder-service](https://github.com/telicent-oss/label-builder-service/blob/main/README.md)

> ### ⚠️ Warning
> telicent-label-builder-service provides [telicent-lib](https://github.com/telicent-oss/telicent-lib) as a dependency.
> telicent-label-builder-service is a dependency of this project!
> telicent-label-builder-service is configurable only through environment variables for the moment.


Assuming the model we want to wrap around REST API is [TelicentModel](../telicent_labels/telicent_model.py) a minimal
program to run the REST service and perform validation would look like the following:

```python
from telicent_labels import TelicentModel

if __name__ == '__main__':
    TelicentModel.run_api()

```

The code above would start the rest service with default values, see `telicent-label-builder-service` documentation.
It would allow us to use the ingest endpoint like so:

```bash
curl -X POST "http://localhost:8000/api/v1/ingest" \
-H "Content-Type: application/json" \
-d '{
  "identifier": "ItemA",
  "classification": "S",
  "permittedOrgs": [
    "ABC",
    "DEF",
    "HIJ"
  ],
  "permittedNats": [
    "GBR",
    "FRA",
    "IRL"
  ],
  "orGroups": [
    "Apple",
    "SOMETHING"
  ],
  "andGroups": [
    "doctor",
    "admin"
  ],
  "originator": "TestOriginator",
  "custodian": "TestCustodian",
  "policyRef": "TestPolicyRef",
  "dataSet": ["ds1", "ds2"],
  "authRef": ["ref1", "ref2"],
  "dispositionProcess": "disp-process-1",
  "dissemination": ["news", "articles"]
}'
{"status":"success",
"security_label":"(classification=S&(permitted_organisations=ABC|permitted_organisations=DEF|permitted_organisations=HIJ)&
(permitted_nationalities=GBR|permitted_nationalities=FRA|permitted_nationalities=IRL)&doctor:and&admin:and&(Apple:or|SOMETHING:or))"}
```