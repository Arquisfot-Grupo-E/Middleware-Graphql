"""
Validation Rules para Ariadne GraphQL
Integra el middleware de throttling con Ariadne
"""

from typing import Any, Collection, Optional
from graphql import ValidationRule, GraphQLError
from graphql.language import DocumentNode
from ariadne.types import ContextValue

from .middleware import validate_query


class ThrottlingValidationRule(ValidationRule):
    """
    Validation Rule personalizado para Ariadne que aplica:
    - Query depth limiting
    - Query complexity analysis
    - Rate limiting por usuario
    """

    def __init__(self, validation_context):
        super().__init__(validation_context)
        self.context = validation_context.context if hasattr(validation_context, 'context') else None

    def enter_document(self, node: DocumentNode, *args):
        """
        Se ejecuta cuando se procesa el documento GraphQL.
        Aplica todas las validaciones de throttling.
        """
        # Obtener el header de autorización del contexto
        authorization_header = None
        if self.context and hasattr(self.context, 'get'):
            request = self.context.get('request')
            if request:
                authorization_header = request.headers.get('authorization')

        # Ejecutar validaciones
        errors = validate_query(node, authorization_header)

        # Reportar errores
        for error in errors:
            self.report_error(error)
