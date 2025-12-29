# resource "aws_ecr_repository" "wildfire_assessment" {
#   name                 = "wildfire-assessment-${var.environment}"
#   image_tag_mutability = "MUTABLE"

#   tags = {
#     Name        = "wildfire-assessment"
#     Environment = var.environment
#   }
# }

# resource "aws_ecr_lifecycle_policy" "wildfire_assessment" {
#   repository = aws_ecr_repository.wildfire_assessment.name

#   policy = <<EOF
# {
#   "rules": [
#     {
#       "rulePriority": 1,
#       "description": "Keep only last 3 images",
#       "selection": {
#         "tagStatus": "any",
#         "countType": "imageCountMoreThan",
#         "countNumber": 3
#       },
#       "action": {
#         "type": "expire"
#       }
#     }
#   ]
# }
# EOF
# }
