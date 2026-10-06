from pydantic import BaseModel, Field

class Usuario(BaseModel):
    id: int = Field(description="ID do usuário")
    email: str 
    nome: str 
    perfil: str 
    status: bool = Field(description="Indica se o usuário está ativo ou inativo")

class GerarChaveRequest(BaseModel):
    nome: str = Field(pattern=r"^[a-zA-Z0-9_-]+$")

class AssinarRequest(BaseModel):
    nome: str = Field(pattern=r"^[a-zA-Z0-9_-]+$")
    texto: str = Field(description="Texto a ser assinado digitalmente")

class VerificarRequest(BaseModel):
    nome: str = Field(pattern=r"^[a-zA-Z0-9_-]+$")
    texto_assinado: str = Field(description="Texto assinado digitalmente")
    assinatura_b64: str = Field(description="Assinatura digital em base64")

class CifrarRequest(BaseModel):
    nome: str = Field(pattern=r"^[a-zA-Z0-9_-]+$")
    texto: str = Field(description="Texto a ser cifrado")

class DecifrarRequest(BaseModel):
    nome: str = Field(pattern=r"^[a-zA-Z0-9_-]+$")
    texto_cifrado: str = Field(description="Texto cifrado em base64")
    nonce: str = Field(description="Nonce utilizado na cifragem em base64")
