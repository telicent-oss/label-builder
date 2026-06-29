Documentation covers the implementation and usage of the Security Label Builder, Telicent Enums, and the Telicent default
model in a data processing context.

1. [Label Builder](./label-builder.md)
   - Overview and implementation of the Security Label Builder.
   - Usage examples for creating and managing security labels.

2. [Telicent Enums](./telicent-enums)
   - Enumerations based on the default Telicent model.
   - Detailed explanation of different label types like `MultiValueLabel` and `SingleValueLabel`.

3. [Telicent Model Implementation](./telicent-header)
   - Implementation details of the Telicent model, which integrates with the Security Label Builder.
   - Description of TelicentMixin used to create customer defined models validating data headers.
   - Code example demonstrating the application of Telicent policy in automatic adapters.

4. [Model Mixin Examples](./model-mixins.md)
   - Worked examples for `TelicentModel` (`telicent_model.py`) and `IDHModel` (`idh_model.py`).
   - Validation behaviour and the resulting Security Label expressions.
   - How to subclass `TelicentMixin` for a custom header shape.
   