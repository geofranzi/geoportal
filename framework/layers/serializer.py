from rest_framework import serializers

from .models import Contact


class ContactWebsiteSerializer(serializers.ModelSerializer):
    work_packages = serializers.SlugRelatedField(many=True, read_only=True, slug_field='name')
    related_org = serializers.SlugRelatedField(read_only=True, slug_field='organisation_short')

    class Meta:
        model = Contact
        fields = (
            'first_name', 'last_name', 'position', 'website', 'organisation_ror', 'person_orcid', 'image', 'related_org', 'work_packages')
